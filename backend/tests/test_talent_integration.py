"""Real PostgreSQL with synthetic fixture input. No TMDB requests."""
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from app import models as m
from app.fixtures import seed_fixture, DATASET, fixture_id
from app.talent.service import build, BuildProblem
from app.main import create_app
from app.catalog import session_for
from test_foundation import settings, FakeDatabase
from test_persistence import database
pytestmark=pytest.mark.integration

def seed(connection):
    with Session(connection) as s,s.begin():seed_fixture(s)

def test_build_rerun_seals_both_versions_and_preserves_fixture(database):
    c=database[0];seed(c)
    first=build(c,DATASET,"ratings-v1");second=build(c,DATASET,"ratings-v1")
    assert first["created"] and not second["created"] and first["feature_hash"]==second["feature_hash"]
    with Session(c) as s:
        assert s.get(m.FeatureVersion,"features:ratings-v1").sealed
        assert s.get(m.PricingVersion,"pricing:ratings-v1").sealed
        assert s.scalar(select(func.count()).select_from(m.RoleFeature).where(m.RoleFeature.feature_id=="features:ratings-v1"))==9
        assert s.get(m.RolePrice,("fixture:pricing-v1",fixture_id("person-director"),"director")).fee_usd==150000
        with pytest.raises(IntegrityError),s.begin_nested():s.execute(text("UPDATE role_prices SET fee_usd=0 WHERE pricing_id='pricing:ratings-v1'"))
        with pytest.raises(IntegrityError),s.begin_nested():s.execute(text("UPDATE role_features SET attributes='{}'::jsonb WHERE feature_id='features:ratings-v1'"))

def test_dry_run_writes_nothing_and_missing_dataset_is_rejected(database):
    c=database[0];seed(c)
    result=build(c,DATASET,"preview",dry_run=True)
    assert result["dry_run"] and not result["created"]
    with Session(c) as s:
        assert s.get(m.FeatureVersion,"features:preview") is None
        assert s.get(m.PricingVersion,"pricing:preview") is None
    with pytest.raises(BuildProblem,match="sealed"):build(c,"missing","invalid")

def test_pricing_failure_rolls_back_feature_rows_too(database):
    c=database[0];seed(c)
    c.execute(text("CREATE FUNCTION fail_phase5_price() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text("CREATE TRIGGER synthetic_price_failure BEFORE INSERT ON role_prices FOR EACH ROW EXECUTE FUNCTION fail_phase5_price()"))
    with pytest.raises(IntegrityError),c.begin_nested():build(c,DATASET,"rollback")
    with Session(c) as s:
        assert s.get(m.FeatureVersion,"features:rollback") is None
        assert s.get(m.PricingVersion,"pricing:rollback") is None

def test_old_versions_survive_new_build_and_label_conflicts_fail(database):
    c=database[0];seed(c);first=build(c,DATASET,"old");build(c,DATASET,"new")
    with Session(c) as s,s.begin():
        assert s.get(m.FeatureVersion,"features:old").content_hash==first["feature_hash"]
        s.add(m.FeatureVersion(id="features:partial",dataset_id=DATASET,ranking_version="fixture:test",configuration={},content_hash="0"*64));s.flush()
    with pytest.raises(BuildProblem,match="Version label"):build(c,DATASET,"partial")

def test_profiles_explain_prices_keep_unknown_ratings_null_and_role_exact(database):
    c=database[0];seed(c);build(c,DATASET,"api-test")
    app=create_app(settings(),FakeDatabase())
    def db():
        with Session(c) as s:yield s
    app.dependency_overrides[session_for]=db
    with TestClient(app) as client:
        versions=client.get("/api/talent/versions").json()["items"]
        assert len(versions)==1 and versions[0]["pricing_id"]=="pricing:api-test"
        result=client.get("/api/talent/pricing:api-test/profiles?role=director&genre=drama")
        assert result.status_code==200,result.text
        p=result.json()["items"][0]
        assert p["fee_is_fictional"] and not p["playable"]
        assert p["notable_works"][0]["audience_rating"] is None
        assert p["notable_works"][0]["credited_jobs"]==["Director"]
        pid=p["person_id"]
        d=client.get(f"/api/talent/pricing:api-test/profiles/{pid}/director?genre=horror")
        assert d.status_code==200,d.text
        assert d.json()["genre_catalog_gap"]
        assert d.json()["hiring_fee_usd"]==p["hiring_fee_usd"] and d.json()["notable_works"]==p["notable_works"]
        assert d.json()["pricing_explanation"]["rounding"]=="ROUND_HALF_UP"
        assert client.get(f"/api/talent/pricing:api-test/profiles/{pid}/composer").status_code==404
        assert client.get("/api/talent/fixture:pricing-v1/profiles?role=director").status_code==404
        assert client.get("/api/talent/pricing:api-test/report").status_code==200
        assert client.get("/api/talent/pricing:api-test/profiles?role=director&limit=1&offset=1").json()["items"]==[]
