from uuid import uuid4
from types import SimpleNamespace as NS
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.analytics import service
from app.drafting.errors import DraftProblem
from test_foundation import FakeDatabase,settings

@pytest.fixture
def client():
    db=FakeDatabase();db.engine=object()
    with TestClient(create_app(settings(),db)) as c:yield c

def test_both_routes_require_header_token_no_store(client):
    base=f'/api/v1/drafts/{uuid4()}'
    for response in [client.get(base+'/analytics-events?access_token='+'x'*43),client.post(base+'/replay',json={'request_id':str(uuid4())})]:assert response.status_code==401 and response.headers['cache-control']=='no-store'

@pytest.mark.parametrize('field',['seed','catalog_id','source_id','tier','score','activity_group'])
def test_replay_rejects_client_gameplay_controls(client,field):
    response=client.post(f'/api/v1/drafts/{uuid4()}/replay',headers={'Authorization':'Bearer '+'x'*43},json={'request_id':str(uuid4()),field:'invalid'});assert response.status_code==422

@pytest.mark.parametrize('status',[404,423])
def test_owner_and_embargo_errors_do_not_expose_private_events(client,monkeypatch,status):
    def blocked(*args):raise DraftProblem(status,'not_available','Unavailable.')
    monkeypatch.setattr(service,'export',blocked);r=client.get(f'/api/v1/drafts/{uuid4()}/analytics-events',headers={'Authorization':'Bearer '+'x'*43});assert r.status_code==status and 'session_key' not in r.text
