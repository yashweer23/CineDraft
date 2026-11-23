from datetime import datetime,timezone,timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from app.main import create_app
from app.accounts import service as accounts
from app.challenges import service as challenges
from app.drafting.errors import DraftProblem
from test_foundation import FakeDatabase,settings

@pytest.fixture
def client():
    db=FakeDatabase();db.engine=object()
    with TestClient(create_app(settings(),db)) as c:yield c

def test_auth_validation_never_echoes_password(client):
    secret='UNIQUE_PRIVATE_PASSWORD'
    r=client.post('/api/v1/accounts/register',json={'username':'x','password':secret,'admin':True})
    assert r.status_code==422 and secret not in r.text and r.headers['cache-control']=='no-store'

def test_registration_normalizes_and_ignores_forwarded_ip(client,monkeypatch):
    captured={}
    def register(engine,body,ip):
        captured.update(name=body.username,ip=ip)
        return dict(access_token='acct_'+'x'*43,expires_at=datetime.now(timezone.utc)+timedelta(hours=8),account=dict(account_id=uuid4(),username=body.username))
    monkeypatch.setattr(accounts,'register',register)
    r=client.post('/api/v1/accounts/register',headers={'X-Forwarded-For':'untrusted'},json={'username':'MiXeD_User','password':'a long private passphrase!'})
    assert r.status_code==201 and r.json()['account']['username']=='mixed_user'
    assert captured['ip']=='testclient' and r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('path,method,body',[('/accounts/me','get',None),('/accounts/logout','post',{}),('/accounts/claim-guest','post',{'guest_token':'a'*43}),('/accounts/password','post',{'current_password':'old','new_password':'a long new passphrase!'}),('/challenges/day-1/attempts','post',{'request_id':str(uuid4())}),('/challenges/day-1/mine','get',None),('/drafts/'+str(uuid4())+'/challenge','get',None)])
def test_private_routes_require_bearer(client,path,method,body):
    assert getattr(client,method)('/api/v1'+path,**({'json':body} if body is not None else {})).status_code==401

def test_throttle_and_seed_embargo_envelopes(client,monkeypatch):
    def limited(*a):raise DraftProblem(429,'authentication_throttled','Wait for the window.')
    def embargo(*a):raise DraftProblem(423,'challenge_results_hidden','Hidden until close.')
    monkeypatch.setattr(accounts,'login',limited);monkeypatch.setattr(challenges,'audit',embargo)
    assert client.post('/api/v1/accounts/login',json={'username':'name','password':'secret'}).status_code==429
    r=client.get('/api/v1/challenges/day-1/audit');assert r.status_code==423 and r.headers['cache-control']=='no-store'

def test_public_listing_has_no_publication_or_score_upload(client,monkeypatch):
    monkeypatch.setattr(challenges,'listing',lambda *a:{'items':[],'next_offset':None})
    assert client.get('/api/v1/challenges').json()=={'items':[],'next_offset':None}
    paths=client.get('/api/openapi.json').json()['paths']
    assert set(paths['/api/v1/challenges'])=={'get'} and not any('submit' in path for path in paths)
    assert client.get('/api/v1/challenges?limit=51').status_code==422
