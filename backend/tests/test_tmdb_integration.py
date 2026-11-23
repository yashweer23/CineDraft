"""Real PostgreSQL with explicitly synthetic source payloads; never calls TMDB."""
from datetime import date
import pytest
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from app import models as m
from app.main import create_app
from app.catalog import session_for
from app.tmdb.importer import new_run,collect,review,publish,run_info,ImportProblem
from test_persistence import database
from test_foundation import settings,FakeDatabase
from tmdb_fixtures import SyntheticClient,movie

pytestmark=pytest.mark.integration

def start(connection,label="test-v1"):
    return new_run(connection,label,ids=[900001],source="fixture",cutoff=date(2026,1,1))

def test_resume_reuses_successful_checkpoints_and_publishes_once(database):
    connection=database[0];run=start(connection);client=SyntheticClient(fail_once=True)
    with pytest.raises(ImportProblem):collect(connection,run,client)
    assert run_info(connection,run)["status"]=="staging"
    collect(connection,run,client)
    assert client.calls.count("configuration")==1 and client.calls.count(900001)==2
    report=review(connection,run)
    assert report["role_people"]["director"]==1 and report["playable"] is False
    assert publish(connection,run)["created"]
    assert not publish(connection,run)["created"]
    with Session(connection) as session:
        assert session.scalar(select(func.count()).select_from(m.Person))==2
        assert session.scalar(select(func.count()).select_from(m.Credit))==3
        assert session.scalar(select(func.count()).select_from(m.FeatureVersion))==0
        assert session.get(m.DatasetVersion,"fixture:test-v1").sealed
        assert all(k.startswith("fixture:") for k in session.scalars(select(m.Person.source_key)))
        with pytest.raises(IntegrityError),session.begin_nested():
            session.execute(text("UPDATE import_resources SET payload='{}'::jsonb"))


def test_catalog_returns_only_role_matching_eligible_films(database):
    connection=database[0];run=start(connection);collect(connection,run,SyntheticClient());publish(connection,run)
    with Session(connection) as s:
        pid=s.scalar(select(m.Person.id).where(m.Person.source_key=="fixture:provider-shaped-person:910002"))
    app=create_app(settings(),FakeDatabase())
    def db_override():
        with Session(connection) as s:yield s
    app.dependency_overrides[session_for]=db_override
    with TestClient(app) as client:
        ds=client.get("/api/catalog/datasets");assert ds.status_code==200
        response=client.get(f"/api/catalog/fixture:test-v1/people/{pid}/films?role=director")
        assert response.status_code==200,response.text
        payload=response.json();assert len(payload["items"])==1 and payload["ranked_notable_works"] is False
        assert payload["items"][0]["credited_jobs"]==["Director"]
        assert client.get(f"/api/catalog/fixture:test-v1/people/{pid}/films?role=actor").json()["items"]==[]
        assert client.get("/api/catalog/not-published/movies").status_code==404
        assert client.get("/api/catalog/fixture:test-v1/movies?limit=999").status_code==422


def test_review_only_run_cannot_publish_and_old_dataset_is_unchanged(database):
    connection=database[0];run=start(connection);collect(connection,run,SyntheticClient());publish(connection,run)
    with Session(connection) as s:old=s.get(m.DatasetVersion,"fixture:test-v1").content_hash
    second=start(connection,"test-v2")
    class ReviewClient(SyntheticClient):
        def movie(self,mid):return movie(id=mid,runtime=None)
    collect(connection,second,ReviewClient())
    assert review(connection,second)["status_counts"]=={"review":1}
    with pytest.raises(ImportProblem):publish(connection,second)
    with Session(connection) as s:
        assert s.get(m.DatasetVersion,"fixture:test-v2") is None
        assert s.get(m.DatasetVersion,"fixture:test-v1").content_hash==old


def test_duplicate_source_credit_rolls_back_publication(database):
    connection=database[0]
    run=new_run(connection,"conflict",ids=[900001,900002],source="fixture",cutoff=date(2026,1,1))
    collect(connection,run,SyntheticClient()) # Same fake credit IDs on different films: intentionally invalid.
    with pytest.raises(ImportProblem):publish(connection,run)
    with Session(connection) as s:
        assert s.get(m.DatasetVersion,"fixture:conflict") is None
        assert s.scalar(select(func.count()).select_from(m.Person))==0
        assert s.get(m.ImportRun,run).status=="staging"
