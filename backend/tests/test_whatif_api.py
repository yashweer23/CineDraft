from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import create_app
from app.whatif import service
from app.drafting.errors import DraftProblem
from test_foundation import FakeDatabase,settings

@pytest.fixture
def client():
    db=FakeDatabase();db.engine=object()
    with TestClient(create_app(settings(),db)) as c:yield c

def paths():
    base='/api/v1/drafts/'+str(uuid4())+'/what-if'
    return [base,base+'/candidates?slot=director',base+'/'+str(uuid4())]

def test_all_lab_routes_require_header_authentication_and_no_store(client):
    for path in paths():
        for query in ('',('&' if '?' in path else '?')+'access_token='+'x'*43):
            r=client.get(path+query);assert r.status_code==401 and r.headers['cache-control']=='no-store'
    r=client.post(paths()[0],json={'request_id':str(uuid4()),'slot':'director','person_id':str(uuid4())});assert r.status_code==401

@pytest.mark.parametrize('field',['seed','samples','score','fee_usd','budget','expected_revision','simulation_version'])
def test_client_cannot_supply_simulation_controls(client,field):
    r=client.post(paths()[0],headers={'Authorization':'Bearer '+'x'*43},json={'request_id':str(uuid4()),'slot':'director','person_id':str(uuid4()),field:123})
    assert r.status_code==422

@pytest.mark.parametrize('route',['create','read','history','candidates'])
def test_embargo_is_reported_without_results(client,monkeypatch,route):
    def embargo(*args):raise DraftProblem(423,'challenge_embargo','Results unlock after closing.')
    monkeypatch.setattr(service,route,embargo);headers={'Authorization':'Bearer '+'x'*43};base=paths()[0]
    if route=='create':r=client.post(base,headers=headers,json={'request_id':str(uuid4()),'slot':'director','person_id':str(uuid4())})
    else:r=client.get(base+({'read':'/'+str(uuid4()),'history':'','candidates':'/candidates?slot=director'}[route]),headers=headers)
    assert r.status_code==423 and r.json()['error']['code']=='challenge_embargo' and r.headers['cache-control']=='no-store'

def test_database_error_is_sanitized(client,monkeypatch):
    def fail(*args):raise OperationalError('private-sql',{},Exception('private-password'))
    monkeypatch.setattr(service,'create',fail)
    r=client.post(paths()[0],headers={'Authorization':'Bearer '+'x'*43},json={'request_id':str(uuid4()),'slot':'director','person_id':str(uuid4())})
    assert r.status_code==503 and 'SAME request ID' in r.text and 'private-' not in r.text

def test_pagination_and_role_are_bounded(client):
    base=paths()[0]+'/candidates';h={'Authorization':'Bearer '+'x'*43}
    for query in ('slot=director&limit=51','slot=director&offset=-1','slot=director&offset=100001','slot=actor'):
        assert client.get(base+'?'+query,headers=h).status_code==422
