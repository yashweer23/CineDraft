"""Phase 9 read-only named rosters must retain draft ownership and frozen inputs."""
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient
from app.main import create_app
from app.drafting import service
from app.drafting.errors import DraftProblem
from test_foundation import settings,FakeDatabase


def test_roster_requires_bearer_and_is_private():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        response=client.get('/api/v1/drafts/'+str(uuid4())+'/roster')
        assert response.status_code==401
        assert response.headers['cache-control']=='no-store'


def test_roster_rejects_wrong_owner_without_leaking_names(monkeypatch):
    db=FakeDatabase();db.engine=object()
    def denied(*args):raise DraftProblem(404,'draft_not_found','Draft not found for this session.')
    monkeypatch.setattr(service,'roster',denied)
    with TestClient(create_app(settings(),db)) as client:
        r=client.get('/api/v1/drafts/'+str(uuid4())+'/roster',headers={'Authorization':'Bearer '+'x'*43})
        assert r.status_code==404 and 'members' not in r.json()


def test_roster_sql_failure_is_sanitized(monkeypatch):
    db=FakeDatabase();db.engine=object()
    def fail(*args):raise SQLAlchemyError('secret db connection')
    monkeypatch.setattr(service,'roster',fail)
    with TestClient(create_app(settings(),db)) as client:
        r=client.get('/api/v1/drafts/'+str(uuid4())+'/roster',headers={'Authorization':'Bearer '+'x'*43})
        assert r.status_code==503 and 'secret' not in r.text


def test_roster_read_adds_no_fields_to_historical_live_draft_contract():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        spec=client.get('/api/openapi.json').json()
        assert list(spec['paths']['/api/v1/drafts/{draft_id}/roster'])==['get']
        assert 'members' not in spec['components']['schemas']['LiveDraft']['properties']
        assert spec['paths']['/api/v1/drafts/{draft_id}/roster']['get']['security']==[{'HTTPBearer':[]}]
