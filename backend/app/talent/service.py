"""Load sealed catalog observations and publish features + prices atomically."""
from collections import defaultdict
import re
from uuid import UUID
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app import models as m
from app.repository import canonical_hash
from app.talent.calculation import (Film, Person, Credit, build_features, build_prices,
    FEATURE_VERSION, RANKING_VERSION, PRICING_VERSION)

class BuildProblem(ValueError):
    pass


def load_catalog(session, dataset_id):
    ds = session.get(m.DatasetVersion, dataset_id)
    if ds is None or not ds.sealed: raise BuildProblem("Select an existing sealed dataset from /api/catalog/datasets.")
    if canonical_hash(ds.configuration) != ds.content_hash: raise BuildProblem("Dataset manifest hash mismatch")
    genre_map = defaultdict(set)
    for mid, genre in session.execute(select(m.MovieGenre.movie_id, m.MovieGenre.genre_id).where(m.MovieGenre.dataset_id == dataset_id)):
        genre_map[str(mid)].add(genre)
    films = [Film(id=str(i.id), source=i.source, source_key=i.source_key, title=s.title,
        release_date=s.release_date, rating=s.audience_rating, votes=s.vote_count,
        popularity=s.popularity, poster_path=s.poster_path, language=s.original_language,
        genres=frozenset(genre_map[str(i.id)]), eligible=s.eligibility == "eligible")
        for s, i in session.execute(select(m.MovieSnapshot, m.Movie).join(m.Movie, m.Movie.id == m.MovieSnapshot.movie_id).where(m.MovieSnapshot.dataset_id == dataset_id))]
    people = [Person(str(p.person_id), p.popularity) for p in session.scalars(select(m.PersonSnapshot).where(m.PersonSnapshot.dataset_id == dataset_id))]
    credits = [Credit(str(c.person_id), str(c.movie_id), c.role, c.job) for c in session.scalars(select(m.Credit).where(m.Credit.dataset_id == dataset_id))]
    return ds, films, people, credits


def calculate(session, dataset_id):
    ds, films, people, credits = load_catalog(session, dataset_id)
    features = build_features(films, people, credits)
    prices = build_prices(features["profiles"])
    feature_config = {"schema_version": FEATURE_VERSION, "dataset_id": ds.id,
        "dataset_manifest_hash": ds.content_hash, "parameters": features["parameters"],
        "input_rows_hash": features["input_hash"], "output_rows_hash": canonical_hash(features["profiles"]),
        "report": features["report"], "scope_version": ds.scope_version,
        "role_mapping_version": ds.role_mapping_version, "source": ds.provenance.get("source", "unknown")}
    return features, prices, feature_config


def build(engine, dataset_id, label, *, dry_run=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,70}", label):
        raise BuildProblem("Version label must use 1–71 lowercase letters, digits, underscores or hyphens.")
    feature_id = "features:" + label; pricing_id = "pricing:" + label
    with Session(engine) as session, session.begin():
        if not dry_run and not session.scalar(text("SELECT pg_try_advisory_xact_lock(41005, 1)")):
            raise BuildProblem("Another talent build is active. Retry when it finishes.")
        features, prices, fc = calculate(session, dataset_id)
        pc = {"schema_version": PRICING_VERSION, "feature_id": feature_id,
            "feature_manifest_hash": canonical_hash(fc), "parameters": prices["parameters"],
            "output_rows_hash": canonical_hash(prices["rows"]), "report": prices["report"]}
        result = {"dataset_id": dataset_id, "feature_id": feature_id, "pricing_id": pricing_id,
            "feature_hash": canonical_hash(fc), "pricing_hash": canonical_hash(pc),
            "feature_report": features["report"], "pricing_report": prices["report"],
            "created": False, "dry_run": dry_run}
        old_f = session.get(m.FeatureVersion, feature_id); old_p = session.get(m.PricingVersion, pricing_id)
        if old_f is not None or old_p is not None:
            if not (old_f is not None and old_p is not None and old_f.sealed and old_p.sealed
                    and old_f.dataset_id == dataset_id and old_p.feature_id == feature_id
                    and old_f.content_hash == result["feature_hash"] and old_p.content_hash == result["pricing_hash"]):
                raise BuildProblem("Version label already belongs to different or incomplete output. Choose a new label.")
            return result
        if dry_run: return result
        feature = m.FeatureVersion(id=feature_id, dataset_id=dataset_id, ranking_version=RANKING_VERSION,
            configuration=fc, content_hash=result["feature_hash"])
        session.add(feature); session.flush()
        for row in features["profiles"]:
            session.add(m.RoleFeature(feature_id=feature_id, dataset_id=dataset_id,
                person_id=UUID(row["person_id"]), role=row["role"], attributes=row["attributes"], evidence=row["evidence"]))
        session.flush(); feature.sealed = True; session.flush()
        pricing = m.PricingVersion(id=pricing_id, feature_id=feature_id,
            configuration=pc, content_hash=result["pricing_hash"])
        session.add(pricing); session.flush()
        for row in prices["rows"]:
            session.add(m.RolePrice(pricing_id=pricing_id, feature_id=feature_id,
                person_id=UUID(row["person_id"]), role=row["role"], fee_usd=row["fee_usd"]))
        session.flush(); pricing.sealed = True; session.flush()
        result["created"] = True
        return result
