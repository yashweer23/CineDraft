"""Explicit import service: checkpoint HTTP reads, review, then publish atomically."""
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timezone
import re
from uuid import UUID, NAMESPACE_URL, uuid5
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app import models as m
from app.domain import GENRES, Role
from app.repository import canonical_hash
from app.tmdb.client import TMDBError
from app.tmdb.payloads import (ConfigurationPayload, DiscoveryPayload, MoviePayload, ReviewOverride)
from app.tmdb.policy import (classify, normalize_credits, GENRE_MAP, POLICY_VERSION, SCOPE_VERSION, ROLE_VERSION)

class ImportProblem(RuntimeError):
    pass

@contextmanager
def exclusive_import(engine):
    # Session-level lock on a dedicated connection; no long database transaction.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(41004, 1)")):
            raise ImportProblem("Another CineDraft import is running. Try again after it finishes.")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(41004, 1)"))

def new_run(engine, label, *, ids=None, pages=1, max_movies=20, cutoff=None, source="tmdb"):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,70}", label):
        raise ImportProblem("Dataset label must use 1–71 lowercase letters, digits, underscores or hyphens.")
    if source not in ("tmdb", "fixture"):
        raise ImportProblem("Invalid source")
    ids = list(dict.fromkeys(ids or []))
    if any(type(i) is not int or not 1 <= i <= 2_147_483_647 for i in ids):
        raise ImportProblem("Movie IDs must be positive integers")
    if not 1 <= pages <= 50 or not 1 <= max_movies <= 2000 or len(ids) > 2000:
        raise ImportProblem("Use 1–50 discovery pages and 1–2000 movies")
    if len(ids) > max_movies:
        raise ImportProblem("Increase --max-movies to cover every explicit ID")
    cutoff = cutoff or datetime.now(timezone.utc).date()
    if cutoff > datetime.now(timezone.utc).date():
        raise ImportProblem("Cutoff cannot be in the future")
    plan = {"policy_version":POLICY_VERSION, "cutoff":cutoff.isoformat(), "ids":ids,
            "pages":pages, "max_movies":max_movies, "selection":"explicit" if ids else "popularity-discovery"}
    with Session(engine) as session, session.begin():
        if session.scalar(select(m.ImportRun.id).where(m.ImportRun.dataset_id == source+":"+label)):
            raise ImportProblem("That dataset label already exists. Resume its run or choose a new version label.")
        run = m.ImportRun(dataset_id=source+":"+label, source=source, plan=plan, report={})
        session.add(run); session.flush()
        return run.id

def run_info(engine, run_id):
    with Session(engine) as session:
        run = session.get(m.ImportRun, run_id)
        if not run: raise ImportProblem("Import run not found")
        resources = session.scalars(select(m.ImportResource).where(m.ImportResource.run_id == run_id)).all()
        return {"run_id":str(run.id), "dataset_id":run.dataset_id, "source":run.source,
                "status":run.status, "plan":run.plan, "report":run.report,
                "resources": [{"key":r.resource_key,"state":r.state,"error_code":r.error_code} for r in resources]}

def checkpoint(engine, run_id, key, fetch, model, expected_id=None):
    with Session(engine) as session:
        run = session.get(m.ImportRun, run_id)
        if not run: raise ImportProblem("Import run not found")
        row = session.get(m.ImportResource, (run_id, key))
        if row and row.state == "ready":
            if canonical_hash(row.payload) != row.payload_hash:
                raise ImportProblem("Checkpoint hash mismatch. Do not publish this import.")
            return model.model_validate(row.payload)
        if run.status == "published": raise ImportProblem("Published imports cannot fetch more resources")
    try:
        value = model.model_validate(fetch())
        if expected_id is not None and value.id != expected_id:
            raise TMDBError("id_mismatch", "TMDB response ID did not match the requested movie.")
        payload = value.model_dump(mode="json")
    except (TMDBError, ValidationError) as error:
        code = error.code if isinstance(error, TMDBError) else "invalid_payload"
        with Session(engine) as session, session.begin():
            row = session.get(m.ImportResource, (run_id,key))
            if row is None:
                row=m.ImportResource(run_id=run_id,resource_key=key,state="failed");session.add(row)
            row.state="failed";row.error_code=code;row.payload=None;row.payload_hash=None
        raise ImportProblem(f"Resource {key} failed ({code}). Resume this run after resolving it.") from None
    with Session(engine) as session, session.begin():
        row = session.get(m.ImportResource, (run_id,key))
        if row is None:
            row=m.ImportResource(run_id=run_id,resource_key=key,state="ready");session.add(row)
        row.state="ready";row.payload=payload;row.payload_hash=canonical_hash(payload)
        row.error_code=None;row.fetched_at=datetime.now(timezone.utc)
    return value

def collect(engine, run_id, client):
    info = run_info(engine,run_id)
    if info["status"] == "published": return info
    plan=info["plan"]
    if plan["policy_version"] != POLICY_VERSION:
        raise ImportProblem("This checkpoint uses another policy version; resume with its original code")
    checkpoint(engine,run_id,"configuration",client.configuration,ConfigurationPayload)
    ids=plan["ids"][:plan["max_movies"]]
    if not ids:
        for page in range(1,plan["pages"]+1):
            data=checkpoint(engine,run_id,f"discover:{page}",lambda page=page:client.discover(page,plan["cutoff"]),DiscoveryPayload)
            if data.page != page: raise ImportProblem("Discovery page mismatch")
            ids=list(dict.fromkeys(ids+[i.id for i in data.results]))[:plan["max_movies"]]
            if len(ids)>=plan["max_movies"] or page>=data.total_pages:break
    for movie_id in ids:
        checkpoint(engine,run_id,f"movie:{movie_id}",lambda movie_id=movie_id:client.movie(movie_id),MoviePayload,expected_id=movie_id)
    return run_info(engine,run_id)

def prepare(session, run, overrides=None):
    if run.plan["policy_version"] != POLICY_VERSION:
        raise ImportProblem("Unsupported import policy version")
    resources=session.scalars(select(m.ImportResource).where(m.ImportResource.run_id==run.id).order_by(m.ImportResource.resource_key)).all()
    cached={r.resource_key:r for r in resources}
    def read(key, cls):
        r=cached.get(key)
        if not r or r.state!="ready": raise ImportProblem("Import is incomplete; resume before review/publish")
        if canonical_hash(r.payload)!=r.payload_hash:raise ImportProblem("Checkpoint hash mismatch")
        return cls.model_validate(r.payload)
    config=read("configuration",ConfigurationPayload)
    ids=run.plan["ids"][:run.plan["max_movies"]]
    if not ids:
        for page in range(1,run.plan["pages"]+1):
            response=read(f"discover:{page}",DiscoveryPayload)
            if response.page!=page:raise ImportProblem("Discovery page mismatch")
            ids=list(dict.fromkeys(ids+[x.id for x in response.results]))[:run.plan["max_movies"]]
            if len(ids)>=run.plan["max_movies"] or page>=response.total_pages:break
    overrides=overrides or {}
    if not set(overrides).issubset({str(i) for i in ids}):raise ImportProblem("Review file contains a movie outside this run")
    movies=[];duplicate_count=0
    for i in sorted(ids):
        movie=read(f"movie:{i}",MoviePayload)
        if movie.id!=i:raise ImportProblem("Movie checkpoint ID mismatch")
        decision=classify(movie,date.fromisoformat(run.plan["cutoff"]),ReviewOverride.model_validate(overrides[str(i)]) if str(i) in overrides else None)
        credits,duplicates=normalize_credits(movie);duplicate_count+=duplicates
        movies.append((movie,decision,credits))
    report={"source":run.source,"synthetic":run.source=="fixture","movies":len(movies),
            "status_counts":dict(Counter(d["status"] for _,d,_ in movies)),
            "review_queue":[{"source_movie_id":v.id,"title":v.title,"reasons":d["reasons"]} for v,d,_ in movies if d["status"]=="review"],
            "exclusions":[{"source_movie_id":v.id,"title":v.title,"reasons":d["reasons"]} for v,d,_ in movies if d["status"]=="excluded"],
            "duplicate_credits_collapsed":duplicate_count,"role_people":{},"genre_movies":{},
            "credit_review_queue":[{"source_movie_id":v.id,"source_person_id":c["person_source_id"],"character":c["character"],"reason":c["mapping_reason"]} for v,_,cs in movies for c in cs if c["kind"]=="cast" and c["role"] is None],
            "unmapped_crew_jobs":dict(Counter(c["job"] for _,_,cs in movies for c in cs if c["kind"]=="crew" and c["role"] is None)),
            "unmapped_or_excluded_credits":sum(c["role"] is None for _,_,cs in movies for c in cs),
            "missing":{key:sum(getattr(v,key) in (None,0,"") for v,_,_ in movies) for key in ["runtime","release_date","poster_path","vote_count"]},
            "playable":False,"playability_note":"Features/prices and exact draft feasibility are not implemented yet."}
    for role in Role:
        report["role_people"][role.value]=len({c["person_source_id"] for _,d,cs in movies if d["status"]=="eligible" for c in cs if c["role"]==role.value})
    for genre in GENRES:
        report["genre_movies"][genre]=sum(d["status"]=="eligible" and any(GENRE_MAP.get(g.id)==genre for g in v.genres) for v,d,_ in movies)
    report["coverage_warnings"]=[f"{role}: fewer than {minimum} eligible people" for role,minimum in [("actor",12),("director",6),("writer",6),("cinematographer",6),("composer",6)] if report["role_people"][role]<minimum]
    return config,movies,report,{r.resource_key:r.payload_hash for r in resources if r.state=="ready"}

def review(engine, run_id, overrides=None):
    with Session(engine) as session,session.begin():
        run=session.get(m.ImportRun,run_id)
        if not run:raise ImportProblem("Import run not found")
        if run.status=="published":return run.report
        _,_,report,_=prepare(session,run,overrides)
        run.report=report
        return report

def publish(engine,run_id,overrides=None):
    with Session(engine) as session,session.begin():
        run=session.scalar(select(m.ImportRun).where(m.ImportRun.id==run_id).with_for_update())
        if not run:raise ImportProblem("Import run not found")
        if run.status=="published":return {"dataset_id":run.dataset_id,"published":True,"created":False}
        config,movies,report,hashes=prepare(session,run,overrides)
        if not report["status_counts"].get("eligible",0):raise ImportProblem("No eligible films; review this run before publishing")
        manifest={"plan":run.plan,"policy_version":POLICY_VERSION,"resource_hashes":hashes,
                  "reviews":overrides or {},"images":config.images.model_dump(),"report":report}
        dataset=m.DatasetVersion(id=run.dataset_id,scope_version=SCOPE_VERSION,role_mapping_version=ROLE_VERSION,
            configuration=manifest,content_hash=canonical_hash(manifest),provenance={"source":run.source,"import_run_id":str(run.id),"import_started_at":run.created_at.isoformat(),"published_at":datetime.now(timezone.utc).isoformat(),"coverage":"Only movies selected by this import; not complete careers"})
        session.add(dataset);session.flush()
        for key,name in GENRES.items():
            session.execute(insert(m.Genre).values(id=key,name=name).on_conflict_do_nothing(index_elements=[m.Genre.id]))
        # Source observations remain in checkpoints; choose the first by stable movie ID for the person snapshot.
        people={}
        for movie,_,_ in movies:
            for c in movie.credits.cast+movie.credits.crew:
                people.setdefault(c.id,c)
        eligible_movies_by_person=defaultdict(set)
        for movie,decision,credits in movies:
            if decision["status"]=="eligible":
                for c in credits:
                    if c["role"]:eligible_movies_by_person[c["person_source_id"]].add(movie.id)
        person_ids={}
        for sid,c in sorted(people.items()):
            key=str(sid) if run.source=="tmdb" else "fixture:provider-shaped-person:"+str(sid)
            identity=uuid5(NAMESPACE_URL,f"cinedraft:{run.source}:person:{sid}")
            session.execute(insert(m.Person).values(id=identity,source=run.source,source_key=key).on_conflict_do_nothing(index_elements=[m.Person.source,m.Person.source_key]))
            identity=session.scalar(select(m.Person.id).where(m.Person.source==run.source,m.Person.source_key==key));person_ids[sid]=identity
            n=len(eligible_movies_by_person[sid])
            session.add(m.PersonSnapshot(dataset_id=dataset.id,person_id=identity,name=c.name,profile_path=c.profile_path,popularity=c.popularity,coverage={"eligible_movies":n,"scope":"imported catalog only","metadata_choice":"first credit observation by movie ID","synthetic":run.source=="fixture"}))
        session.flush()
        credit_keys={}
        for movie,decision,credits in movies:
            key=str(movie.id) if run.source=="tmdb" else "fixture:provider-shaped-movie:"+str(movie.id)
            identity=uuid5(NAMESPACE_URL,f"cinedraft:{run.source}:movie:{movie.id}")
            session.execute(insert(m.Movie).values(id=identity,source=run.source,source_key=key).on_conflict_do_nothing(index_elements=[m.Movie.source,m.Movie.source_key]))
            identity=session.scalar(select(m.Movie.id).where(m.Movie.source==run.source,m.Movie.source_key==key))
            session.add(m.MovieSnapshot(dataset_id=dataset.id,movie_id=identity,title=movie.title,original_language=movie.original_language,
                release_date=movie.release_date,runtime_minutes=decision["runtime"],poster_path=movie.poster_path,
                audience_rating=movie.vote_average if movie.vote_count and movie.vote_average is not None else None,
                vote_count=movie.vote_count,popularity=movie.popularity,eligibility=decision["status"],eligibility_reason="; ".join(decision["reasons"])[:500],
                provenance={"source":run.source,"source_movie_id":movie.id,"decision":decision,"source_genres":[g.model_dump() for g in movie.genres],"resource_hash":hashes[f"movie:{movie.id}"],"endpoint":f"/movie/{movie.id}?append_to_response=credits,keywords"}))
            session.flush()
            for genre in sorted({GENRE_MAP[g.id] for g in movie.genres if g.id in GENRE_MAP}):
                session.add(m.MovieGenre(dataset_id=dataset.id,movie_id=identity,genre_id=genre))
            for c in credits:
                if c["dedupe_key"] in credit_keys and credit_keys[c["dedupe_key"]]!=c:
                    raise ImportProblem("Conflicting source credit IDs across movies; publication rolled back")
                credit_keys[c["dedupe_key"]]=c
                session.add(m.Credit(dataset_id=dataset.id,person_id=person_ids[c["person_source_id"]],movie_id=identity,
                    dedupe_key=c["dedupe_key"],source_credit_id=c["source_credit_id"],kind=c["kind"],job=c["job"],department=c["department"],character=c["character"],cast_order=c["cast_order"],role=c["role"],
                    provenance={"source":run.source,"mapping_version":ROLE_VERSION,"mapping_reason":c["mapping_reason"],"movie_resource_hash":hashes[f"movie:{movie.id}"]}))
            session.flush()
        dataset.sealed=True
        session.flush()
        run.status="published";run.report=report;run.published_at=datetime.now(timezone.utc)
        session.flush()
        return {"dataset_id":dataset.id,"published":True,"created":True,"report":report}
