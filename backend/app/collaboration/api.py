"""Read-only version-pinned graph views. No upstream requests or graph recomputation."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import select, or_
from app import models as m
from app.catalog import DB, Limit, picture
from app.domain import Role
from app.repository import canonical_hash
from app.schemas import ErrorEnvelope
from app.collaboration.calculation import ALGORITHM_VERSION, NO_SHARED, canonical_pair, edge_key
from app.collaboration.schemas import VersionPage, NodePage, EdgePage, PairResult, EvidencePage, GraphReport

Offset = Annotated[int, Query(ge=0, le=1000000)]
EdgeId = Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")]
router = APIRouter(prefix="/api/collaboration", tags=["Collaboration evidence"],
    responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})


def versions_query():
    return (select(m.GraphVersion, m.DatasetVersion)
        .join(m.DatasetVersion, m.DatasetVersion.id == m.GraphVersion.dataset_id)
        .where(m.GraphVersion.sealed.is_(True), m.DatasetVersion.sealed.is_(True),
            m.GraphVersion.algorithm_version == ALGORITHM_VERSION))


def version_view(g, ds):
    if canonical_hash(g.configuration) != g.content_hash:
        raise HTTPException(503, "Graph manifest integrity check failed.")
    return dict(graph_id=g.id, dataset_id=ds.id, graph_hash=g.content_hash,
        algorithm_version=g.algorithm_version, created_at=g.created_at,
        source=ds.provenance.get("source", "unknown"), report=g.configuration["report"])


def version(session, graph_id):
    row = session.execute(versions_query().where(m.GraphVersion.id == graph_id)).one_or_none()
    if row is None:
        raise HTTPException(404, "Published Phase 6 graph version not found.")
    version_view(*row)
    return row


def node_query(graph_id):
    return (select(m.GraphNode, m.PersonSnapshot, m.Person)
        .join(m.PersonSnapshot, (m.PersonSnapshot.person_id == m.GraphNode.person_id) & (m.PersonSnapshot.dataset_id == m.GraphNode.dataset_id))
        .join(m.Person, m.Person.id == m.GraphNode.person_id).where(m.GraphNode.graph_id == graph_id))


def node_view(node, snapshot, person):
    return dict(person_id=person.id, name=snapshot.name, role=node.role,
        source=person.source, source_key=person.source_key, film_count=node.film_count)


def node_map(session, graph_id, ids):
    if not ids:
        return {}
    return {(str(n.person_id), n.role): node_view(n, s, p)
        for n, s, p in session.execute(node_query(graph_id).where(m.GraphNode.person_id.in_(ids)))}


def edge_view(edge, nodes):
    return dict(edge_id=edge.edge_id, a=nodes[(str(edge.person_a), edge.role_a)],
        b=nodes[(str(edge.person_b), edge.role_b)], shared_movie_count=edge.shared_movie_count,
        bonus=edge.bonus, capped=edge.shared_movie_count >= 3)


def next_offset(rows, limit, offset):
    return offset + limit if len(rows) > limit else None


@router.get("/versions", response_model=VersionPage)
def versions(session: DB, dataset_id: str | None = None, limit: Limit = 20, offset: Offset = 0):
    q = versions_query()
    if dataset_id is not None:
        q = q.where(m.GraphVersion.dataset_id == dataset_id)
    rows = session.execute(q.order_by(m.GraphVersion.id).offset(offset).limit(limit + 1)).all()
    return {"items": [version_view(*r) for r in rows[:limit]], "next_offset": next_offset(rows, limit, offset)}


@router.get("/{graph_id}/nodes", response_model=NodePage)
def nodes(graph_id: str, session: DB, role: Role | None = None,
          q: Annotated[str, Query(max_length=80)] = "", limit: Limit = 20, offset: Offset = 0):
    version(session, graph_id)
    query = node_query(graph_id)
    if role is not None:
        query = query.where(m.GraphNode.role == role.value)
    if q.strip():
        query = query.where(m.PersonSnapshot.name.icontains(q.strip(), autoescape=True))
    rows = session.execute(query.order_by(m.GraphNode.person_id, m.GraphNode.role).offset(offset).limit(limit + 1)).all()
    return {"graph_id": graph_id, "items": [node_view(*r) for r in rows[:limit]], "next_offset": next_offset(rows, limit, offset)}


@router.get("/{graph_id}/edges", response_model=EdgePage)
def edges(graph_id: str, session: DB, role: Role | None = None, person_id: UUID | None = None,
          limit: Limit = 20, offset: Offset = 0):
    version(session, graph_id)
    query = select(m.GraphEdge).where(m.GraphEdge.graph_id == graph_id)
    # When both filters are supplied they must apply to the SAME endpoint.
    a, b = [], []
    if role is not None:
        a.append(m.GraphEdge.role_a == role.value); b.append(m.GraphEdge.role_b == role.value)
    if person_id is not None:
        a.append(m.GraphEdge.person_a == person_id); b.append(m.GraphEdge.person_b == person_id)
    if a:
        from sqlalchemy import and_
        query = query.where(or_(and_(*a), and_(*b)))
    rows = session.scalars(query.order_by(m.GraphEdge.shared_movie_count.desc(), m.GraphEdge.edge_id).offset(offset).limit(limit + 1)).all()
    people = node_map(session, graph_id, {pid for e in rows[:limit] for pid in (e.person_a, e.person_b)})
    return {"graph_id": graph_id, "items": [edge_view(e, people) for e in rows[:limit]], "next_offset": next_offset(rows, limit, offset)}


@router.get("/{graph_id}/pair", response_model=PairResult)
def pair(graph_id: str, person_a: UUID, role_a: Role, person_b: UUID, role_b: Role, session: DB):
    graph, ds = version(session, graph_id)
    try:
        a, b = canonical_pair(person_a, role_a, person_b, role_b)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    people = node_map(session, graph.id, [person_a, person_b])
    if a not in people or b not in people:
        raise HTTPException(404, "One or both people have no eligible credits in the selected role and dataset.")
    edge = session.get(m.GraphEdge, (graph.id, edge_key(a, b)))
    value = edge_view(edge, people) if edge else dict(edge_id=None, a=people[a], b=people[b], shared_movie_count=0, bonus=0, capped=False)
    return {"graph_id": graph.id, "dataset_id": ds.id, "edge": value,
        "message": "Shared credits found in this dataset." if edge else NO_SHARED}


@router.get("/{graph_id}/edges/{edge_id}/films", response_model=EvidencePage)
def films(graph_id: str, edge_id: EdgeId, session: DB, limit: Limit = 20, offset: Offset = 0):
    graph, ds = version(session, graph_id)
    edge = session.get(m.GraphEdge, (graph.id, edge_id))
    if edge is None:
        raise HTTPException(404, "Collaboration edge not found in this graph.")
    people = node_map(session, graph.id, [edge.person_a, edge.person_b])
    rows = session.execute(select(m.GraphEvidence, m.MovieSnapshot, m.Movie)
        .join(m.MovieSnapshot, (m.MovieSnapshot.dataset_id == m.GraphEvidence.dataset_id) & (m.MovieSnapshot.movie_id == m.GraphEvidence.movie_id))
        .join(m.Movie, m.Movie.id == m.GraphEvidence.movie_id)
        .where(m.GraphEvidence.graph_id == graph.id, m.GraphEvidence.edge_id == edge_id)
        .order_by(m.GraphEvidence.movie_id).offset(offset).limit(limit + 1)).all()
    return {"graph_id": graph.id, "dataset_id": ds.id, "edge": edge_view(edge, people),
        "items": [dict(movie_id=i.id, title=s.title, year=s.release_date.year if s.release_date else None,
            source=i.source, source_key=i.source_key,
            source_url=f"https://www.themoviedb.org/movie/{i.source_key}" if i.source == "tmdb" else None,
            poster_url=picture(ds, s.poster_path, "poster"), jobs_a=e.jobs_a, jobs_b=e.jobs_b) for e, s, i in rows[:limit]],
        "next_offset": next_offset(rows, limit, offset)}


@router.get("/{graph_id}/report", response_model=GraphReport)
def report(graph_id: str, session: DB):
    graph, ds = version(session, graph_id)
    return {"version": version_view(graph, ds), **{key: graph.configuration[key] for key in
        ("parameters", "dataset_manifest_hash", "input_rows_hash", "output_rows_hash")}}
