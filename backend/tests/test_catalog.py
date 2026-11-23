from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from test_foundation import FakeDatabase,settings


def test_raw_catalog_and_release_routes_are_live():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        spec=client.get("/api/openapi.json").json()
        assert "/api/catalog/datasets" in spec["paths"]
        assert "/api/catalog/{dataset_id}/people/{person_id}/films" in spec["paths"]
        assert "/api/v1/drafts/{draft_id}/release" in spec["paths"]
        assert "not endorsed or certified" in client.get("/api/catalog/attribution").json()["notice"]


def test_token_is_optional_for_api_startup_and_hidden_in_settings():
    config=Settings(_env_file=None,db_name="test",db_user="test",db_password="test",tmdb_read_access_token="synthetic-private-token")
    assert "synthetic-private-token" not in repr(config)
    with TestClient(create_app(config,FakeDatabase())) as client:
        assert "synthetic-private-token" not in client.get("/api/openapi.json").text
