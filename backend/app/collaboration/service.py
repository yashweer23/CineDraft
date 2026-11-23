"""Explicit, atomic, offline graph publication from a sealed dataset."""
import re
from uuid import UUID
from sqlalchemy import insert, text
from sqlalchemy.orm import Session
from app import models as m
from app.repository import canonical_hash
from app.talent.service import load_catalog, BuildProblem
from app.collaboration.calculation import build_graph, ALGORITHM_VERSION


def insert_batches(session, model, rows):
    for start in range(0, len(rows), 1000):
        session.execute(insert(model), rows[start:start + 1000])


def build(engine, dataset_id, label, *, dry_run=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,70}", label):
        raise BuildProblem("Version label must use 1–71 lowercase letters, digits, underscores or hyphens.")
    graph_id = "graph:" + label
    with Session(engine) as session, session.begin():
        if not dry_run and not session.scalar(text("SELECT pg_try_advisory_xact_lock(41006, 1)")):
            raise BuildProblem("Another graph build is active. Retry when it finishes.")
        ds, films, people, credits = load_catalog(session, dataset_id)
        graph = build_graph(films, people, credits)
        config = {"schema_version": ALGORITHM_VERSION, "dataset_id": ds.id,
            "dataset_manifest_hash": ds.content_hash, "scope_version": ds.scope_version,
            "role_mapping_version": ds.role_mapping_version, "source": ds.provenance.get("source", "unknown"),
            "parameters": graph["parameters"], "input_rows_hash": graph["input_hash"],
            "output_rows_hash": graph["output_hash"], "report": graph["report"]}
        digest = canonical_hash(config)
        result = {"graph_id": graph_id, "dataset_id": ds.id, "graph_hash": digest,
            "algorithm_version": ALGORITHM_VERSION, "report": graph["report"],
            "created": False, "dry_run": dry_run}
        old = session.get(m.GraphVersion, graph_id)
        if old is not None:
            if not (old.sealed and old.dataset_id == ds.id and old.algorithm_version == ALGORITHM_VERSION
                    and old.content_hash == digest and canonical_hash(old.configuration) == digest):
                raise BuildProblem("Version label belongs to different or incomplete output. Choose a new label.")
            return result
        if dry_run:
            return result
        version = m.GraphVersion(id=graph_id, dataset_id=ds.id, algorithm_version=ALGORITHM_VERSION,
            configuration=config, content_hash=digest)
        session.add(version); session.flush()
        insert_batches(session, m.GraphNode, [dict(graph_id=graph_id, dataset_id=ds.id,
            person_id=UUID(n["person_id"]), role=n["role"], film_count=n["film_count"]) for n in graph["nodes"]])
        edges, evidence = [], []
        for edge in graph["edges"]:
            edges.append({k: v for k, v in edge.items() if k != "evidence"} | {
                "graph_id": graph_id, "person_a": UUID(edge["person_a"]), "person_b": UUID(edge["person_b"])})
            evidence.extend(dict(graph_id=graph_id, dataset_id=ds.id, edge_id=edge["edge_id"],
                movie_id=UUID(row["movie_id"]), jobs_a=row["jobs_a"], jobs_b=row["jobs_b"]) for row in edge["evidence"])
        insert_batches(session, m.GraphEdge, edges)
        insert_batches(session, m.GraphEvidence, evidence)
        version.sealed = True; session.flush()
        result["created"] = True
        return result
