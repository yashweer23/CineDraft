from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import create_app
from app.simulation import service
from app.drafting.errors import DraftProblem
from test_foundation import FakeDatabase,settings


def test_release_result_and_status_require_header_authentication():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        base='/api/v1/drafts/'+str(uuid4())
        for route in ('release','retry-simulation'):
            response=client.post(base+'/'+route,json={'request_id':str(uuid4()),'expected_revision':9})
            assert response.status_code==401 and response.headers['cache-control']=='no-store'
        for route in ('result','simulation'):
            assert client.get(base+'/'+route).status_code==401
            assert client.get(base+'/'+route+'?access_token='+'x'*43).status_code==401


def test_release_forbids_client_scores_seed_and_other_simulation_controls():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        base='/api/v1/drafts/'+str(uuid4());headers={'Authorization':'Bearer '+'x'*43}
        body={'request_id':str(uuid4()),'expected_revision':9}
        for route in ('release','retry-simulation'):
            for field in ('seed','studio_score','noise','simulation_version','iterations','gross_usd'):
                assert client.post(base+'/'+route,headers=headers,json=body|{field:'untrusted'}).status_code==422


def test_database_failure_is_sanitized_and_requests_exact_retry(monkeypatch):
    db=FakeDatabase();db.engine=object()
    def unavailable(*args):raise OperationalError('private-sql',{},Exception('password-private'))
    monkeypatch.setattr(service,'release',unavailable)
    with TestClient(create_app(settings(),db)) as client:
        response=client.post('/api/v1/drafts/'+str(uuid4())+'/release',headers={'Authorization':'Bearer '+'x'*43},json={'request_id':str(uuid4()),'expected_revision':9})
        assert response.status_code==503
        assert 'SAME request ID' in response.text and 'password-private' not in response.text and 'private-sql' not in response.text


def test_result_does_not_disclose_other_owner_state(monkeypatch):
    db=FakeDatabase();db.engine=object()
    def missing(*args):raise DraftProblem(404,'draft_not_found','Draft not found for this session.')
    monkeypatch.setattr(service,'result',missing)
    with TestClient(create_app(settings(),db)) as client:
        response=client.get('/api/v1/drafts/'+str(uuid4())+'/result',headers={'Authorization':'Bearer '+'x'*43})
        assert response.status_code==404 and response.json()['error']['code']=='draft_not_found'


def test_current_api_describes_all_phase8_routes_with_security():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        spec=client.get('/api/openapi.json').json()
        for suffix,method in [('release','post'),('retry-simulation','post'),('simulation','get'),('result','get')]:
            operation=spec['paths']['/api/v1/drafts/{draft_id}/'+suffix][method]
            assert operation['security']==[{'HTTPBearer':[]}]
        assert spec['info']['version']=='0.15.0'
        assert client.get('/api/health').json()['version']=='0.15.0'
