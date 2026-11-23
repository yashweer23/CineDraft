"""Read-only computed talent profiles. All responses pin a published price version."""
from uuid import UUID
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app import models as m
from app.catalog import DB, Limit, Offset, picture
from app.contracts import GenreId
from app.domain import Role
from app.schemas import ErrorEnvelope
from app.talent.calculation import FEATURE_VERSION, PRICING_VERSION, RANKING_VERSION, price_profile
from app.talent.schemas import TalentVersions, TalentPage, TalentDetail, TalentReport

router = APIRouter(prefix="/api/talent", tags=["Talent ratings and fictional fees"],
    responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})


def version_view(p, f, ds):
    return dict(dataset_id=ds.id, feature_id=f.id, pricing_id=p.id, feature_version=FEATURE_VERSION,
        pricing_version=PRICING_VERSION, ranking_version=f.ranking_version,
        feature_hash=f.content_hash, pricing_hash=p.content_hash, created_at=p.created_at,
        source=ds.provenance.get("source", "unknown"))


def versions_query():
    return (select(m.PricingVersion, m.FeatureVersion, m.DatasetVersion)
        .join(m.FeatureVersion, m.FeatureVersion.id == m.PricingVersion.feature_id)
        .join(m.DatasetVersion, m.DatasetVersion.id == m.FeatureVersion.dataset_id)
        .where(m.PricingVersion.sealed.is_(True), m.FeatureVersion.sealed.is_(True), m.DatasetVersion.sealed.is_(True),
            m.FeatureVersion.ranking_version == RANKING_VERSION,
            m.FeatureVersion.configuration["schema_version"].as_string() == FEATURE_VERSION,
            m.PricingVersion.configuration["schema_version"].as_string() == PRICING_VERSION))


def version(session, pricing_id):
    row = session.execute(versions_query().where(m.PricingVersion.id == pricing_id)).one_or_none()
    if row is None: raise HTTPException(404, "Published Phase 5 pricing version not found.")
    return row


def profile_query(p, f):
    return (select(m.RoleFeature, m.RolePrice, m.PersonSnapshot, m.Person)
        .join(m.RolePrice, (m.RolePrice.feature_id == m.RoleFeature.feature_id) & (m.RolePrice.person_id == m.RoleFeature.person_id) & (m.RolePrice.role == m.RoleFeature.role))
        .join(m.PersonSnapshot, (m.PersonSnapshot.dataset_id == m.RoleFeature.dataset_id) & (m.PersonSnapshot.person_id == m.RoleFeature.person_id))
        .join(m.Person, m.Person.id == m.PersonSnapshot.person_id)
        .where(m.RoleFeature.feature_id == f.id, m.RolePrice.pricing_id == p.id))


def film_map(session, ds, rows):
    ids = {UUID(w["movie_id"]) for feature, *_ in rows for w in feature.evidence["notable_works"]}
    if not ids: return {}
    return {str(i.id): (s, i) for s, i in session.execute(select(m.MovieSnapshot, m.Movie)
        .join(m.Movie, m.Movie.id == m.MovieSnapshot.movie_id)
        .where(m.MovieSnapshot.dataset_id == ds.id, m.MovieSnapshot.movie_id.in_(ids), m.MovieSnapshot.eligibility == "eligible"))}


def view(p, f, ds, row, films, genre):
    rf, rp, snapshot, person = row; a = rf.attributes; e = rf.evidence
    notable = []
    for work in e["notable_works"]:
        movie, identity = films[work["movie_id"]]
        notable.append(dict(movie_id=identity.id, source=identity.source, source_key=identity.source_key,
            title=movie.title, year=movie.release_date.year if movie.release_date else None,
            poster_url=picture(ds, movie.poster_path, "poster"),
            audience_rating=float(movie.audience_rating) if movie.audience_rating is not None and movie.vote_count else None,
            vote_count=movie.vote_count, credited_jobs=work["credited_jobs"], rank=work["rank"],
            notability=work["notability"], reception_available=work["reception_available"], components=work["components"]))
    return dict(person_id=person.id, name=snapshot.name, source=person.source, source_key=person.source_key,
        role=rf.role, profile_url=picture(ds, snapshot.profile_path, "profile"),
        dataset_id=ds.id, feature_id=f.id, pricing_id=p.id, ranking_version=f.ranking_version,
        hiring_fee_usd=rp.fee_usd, talent_strength=a["talent_strength"], reception=a["reception"],
        experience=a["experience"], versatility=a["versatility"], popularity_percentile=a["popularity_percentile"],
        selected_genre=genre, genre_fit=a["genre_fit"][genre], genre_evidence_movies=e["genre_counts"][genre],
        genre_catalog_gap=genre in e["genre_catalog_gaps"], specialties=a["specialties"],
        career_span_years=a["career_span_years"], coverage=a["coverage"], notable_works=notable)


@router.get("/versions", response_model=TalentVersions)
def versions(session: DB, dataset_id: str | None = None, limit: Limit = 20, offset: Offset = 0):
    q = versions_query()
    if dataset_id is not None: q = q.where(m.DatasetVersion.id == dataset_id)
    rows = session.execute(q.order_by(m.PricingVersion.id).offset(offset).limit(limit + 1)).all()
    return {"items": [version_view(*r) for r in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/{pricing_id}/profiles", response_model=TalentPage)
def profiles(pricing_id: str, role: Role, session: DB, genre: GenreId = "drama", limit: Limit = 20, offset: Offset = 0):
    p, f, ds = version(session, pricing_id)
    rows = session.execute(profile_query(p, f).where(m.RoleFeature.role == role.value)
        .order_by(m.RoleFeature.attributes["talent_strength"].as_float().desc(), m.Person.id)
        .offset(offset).limit(limit + 1)).all()
    films = film_map(session, ds, rows[:limit])
    return {"items": [view(p, f, ds, r, films, genre) for r in rows[:limit]], "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/{pricing_id}/profiles/{person_id}/{role}", response_model=TalentDetail)
def detail(pricing_id: str, person_id: UUID, role: Role, session: DB, genre: GenreId = "drama"):
    p, f, ds = version(session, pricing_id)
    row = session.execute(profile_query(p, f).where(m.Person.id == person_id, m.RoleFeature.role == role.value)).one_or_none()
    if row is None: raise HTTPException(404, "Person has no profile in this role and version.")
    computed = price_profile(role.value, row[0].attributes)
    if computed["fee_usd"] != row[1].fee_usd: raise HTTPException(503, "Stored price does not match its calculation version.")
    return view(p, f, ds, row, film_map(session, ds, [row]), genre) | {"evidence": row[0].evidence,
        "pricing_explanation": computed["explanation"], "feature_parameters": f.configuration["parameters"],
        "pricing_parameters": p.configuration["parameters"]}


@router.get("/{pricing_id}/report", response_model=TalentReport)
def report(pricing_id: str, session: DB):
    p, f, ds = version(session, pricing_id)
    return {"versions": version_view(p, f, ds), "features": f.configuration["report"], "pricing": p.configuration["report"]}
