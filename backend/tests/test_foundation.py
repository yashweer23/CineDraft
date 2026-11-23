import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


class FakeDatabase:
    def __init__(self, available=True):
        self.available = available
        self.closed = False

    def ping(self):
        return self.available

    def close(self):
        self.closed = True


def settings(**overrides):
    return Settings(_env_file=None, db_name="test", db_user="test",
                    db_password="test-password-private", **overrides)


def test_live_ready_and_shutdown():
    database = FakeDatabase()
    with TestClient(create_app(settings(), database)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["service"] == "cinedraft-api"
        assert response.headers["X-Request-ID"]
        assert client.get("/api/health/ready").json() == {"status": "ready", "database": "connected"}
    assert database.closed


def test_database_failure_is_honest_and_recoverable():
    database = FakeDatabase(False)
    with TestClient(create_app(settings(), database)) as client:
        assert client.get("/api/health").status_code == 200
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"
        assert response.json()["request_id"] == response.headers["X-Request-ID"]
        assert "test-password-private" not in response.text
        database.available = True
        assert client.get("/api/health/ready").status_code == 200


def test_unknown_routes_and_methods_use_error_envelope():
    with TestClient(create_app(settings(), FakeDatabase())) as client:
        for method, path, status in [("get", "/api/missing", 404), ("post", "/api/health", 405)]:
            response = getattr(client, method)(path)
            assert response.status_code == status
            assert response.json()["error"]["code"] == f"http_{status}"


def test_cors_allows_only_explicit_origins():
    with TestClient(create_app(settings(), FakeDatabase())) as client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        blocked = client.get("/api/health", headers={"Origin": "https://unrelated.example"})
        assert "access-control-allow-origin" not in blocked.headers


@pytest.mark.parametrize("origin", ["*", "http://localhost:5173/path", "file://local", "https://user:pass@example.com"])
def test_bad_origins_are_rejected(origin):
    with pytest.raises(ValidationError):
        settings(cors_origins=[origin])


def test_settings_reject_invalid_port_and_hide_password():
    with pytest.raises(ValidationError):
        settings(db_port=70000)
    config = settings()
    assert "test-password-private" not in repr(config)
    assert "test-password-private" not in str(config.database_url())


def test_missing_configuration_has_actionable_message(monkeypatch):
    import app.main as main
    # Force a genuinely empty env source independently of a developer's .env.
    def invalid_settings():
        raise ValidationError.from_exception_data("Settings", [
            {"type": "missing", "loc": ("db_password",), "input": {}}
        ])
    monkeypatch.setattr(main, "Settings", invalid_settings)
    with pytest.raises(RuntimeError, match="setup-env.cjs.*db_password"):
        main.create_app()


def test_malformed_environment_json_is_actionable(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "not-json")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be a JSON array"):
        create_app()


def test_unexpected_database_error_is_sanitized():
    class BrokenDatabase(FakeDatabase):
        def ping(self):
            raise RuntimeError("driver-secret-password")
    with TestClient(create_app(settings(), BrokenDatabase())) as client:
        response = client.get("/api/health/ready")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "internal_error"
        assert "driver-secret-password" not in response.text


def test_openapi_contains_readiness_error_contract():
    with TestClient(create_app(settings(), FakeDatabase())) as client:
        spec = client.get("/api/openapi.json").json()
        assert "503" in spec["paths"]["/api/health/ready"]["get"]["responses"]
