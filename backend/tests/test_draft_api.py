from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.drafting.auth import token_hash
from app.drafting.errors import DraftProblem
from test_foundation import settings,FakeDatabase


def test_private_drafts_require_valid_shaped_bearer_and_no_store():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        for token in (None,'short','x'*42,'x'*44,'a b'+'x'*40):
            headers={'Authorization':'Bearer '+token} if token else {}
            for path in ('/api/v1/drafts','/api/v1/drafts/'+str(uuid4())):
                response=client.get(path,headers=headers)
                assert response.status_code==401,response.text
                assert response.headers['www-authenticate']=='Bearer'
                assert response.headers['cache-control']=='no-store'
        assert client.get('/api/v1/drafts?access_token='+'x'*43).status_code==401


def test_game_requests_reject_client_controlled_state_before_mutation():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        headers={'Authorization':'Bearer '+'x'*43};base={'request_id':str(uuid4()),'genre_id':'crime','tier':'studio'}
        for field in ('seed','fee_usd','graph_id','pricing_id','owner_key_hash','talent_remaining_usd'):
            response=client.post('/api/v1/drafts',headers=headers,json=base|{field:'untrusted'})
            assert response.status_code==422,response.text
        response=client.post('/api/v1/drafts/'+str(uuid4())+'/picks',headers=headers,json={'request_id':str(uuid4()),'expected_revision':-1,'offer_id':str(uuid4()),'person_id':str(uuid4())})
        assert response.status_code==422


def test_live_contract_has_authenticated_actions_including_simulation():
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        spec=client.get('/api/openapi.json').json()
        for path,operations in spec['paths'].items():
            if path.startswith('/api/v1/drafts') or path=='/api/v1/sessions/revoke':
                assert all(op['security']==[{'HTTPBearer':[]}] for op in operations.values())
        assert '/api/v1/drafts/{draft_id}/release' in spec['paths']
        assert 'graph_id' in spec['components']['schemas']['DraftVersions']['properties']
        assert 'access_token' not in spec['components']['schemas']['LiveDraft']['properties']


def test_capability_hash_is_not_the_capability():
    token='x'*43
    assert len(token_hash(token))==64 and token not in token_hash(token)
    with pytest.raises(DraftProblem):token_hash('bad')


def test_structured_stale_revision_response(monkeypatch):
    from app.drafting import service
    database=FakeDatabase();database.engine=object()
    def stale(*args):raise DraftProblem(409,'stale_revision','Refresh draft.',7)
    monkeypatch.setattr(service,'mutate',stale)
    with TestClient(create_app(settings(),database)) as client:
        response=client.post('/api/v1/drafts/'+str(uuid4())+'/finalize',headers={'Authorization':'Bearer '+'x'*43},json={'request_id':str(uuid4()),'expected_revision':3})
        assert response.status_code==409
        assert response.json()['error']['current_revision']==7
        assert response.json()['request_id']==response.headers['x-request-id']
