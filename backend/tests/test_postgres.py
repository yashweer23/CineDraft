import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import make_url

from app.config import Settings
from app.main import create_app


@pytest.mark.integration
def test_real_postgresql_readiness():
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set TEST_DATABASE_URL to run the real PostgreSQL integration check")
    url = make_url(value)
    assert url.get_backend_name() == "postgresql", "This check requires PostgreSQL, not SQLite"
    settings = Settings(_env_file=None, environment="test", db_host=url.host,
                        db_port=url.port or 5432, db_name=url.database,
                        db_user=url.username, db_password=url.password)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health/ready")
        assert response.status_code == 200, response.json()
        assert response.json()["database"] == "connected"
