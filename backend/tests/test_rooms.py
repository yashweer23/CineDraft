from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import create_app
from app.rooms import schemas as w, service
from app.rooms.policy import require_pick, timeout_choice
from app.drafting.errors import DraftProblem
from test_foundation import settings, FakeDatabase

NOW = datetime(2026, 11, 7, tzinfo=timezone.utc)

def test_turn_alternation_and_deadline_boundary():
    for count in range(8):
        require_pick('active', count, count, count % 2, count, NOW+timedelta(seconds=1), NOW)
        with pytest.raises(DraftProblem, match='Wait for your partner'):
            require_pick('active', count, count, 1-count % 2, count, NOW+timedelta(seconds=1), NOW)
    with pytest.raises(DraftProblem) as error:
        require_pick('active', 0, 0, 0, 0, NOW, NOW)
    assert error.value.code == 'turn_expired'

@pytest.mark.parametrize('state', ['waiting', 'complete', 'cancelled'])
def test_no_pick_outside_active(state):
    with pytest.raises(DraftProblem) as error:
        require_pick(state, 0, 0, 0, 0, None, NOW)
    assert error.value.code == 'room_inactive'

def test_stale_request_cannot_target_next_turn():
    with pytest.raises(DraftProblem) as error:
        require_pick('active', 5, 3, 1, 3, NOW+timedelta(seconds=1), NOW)
    assert error.value.code == 'stale_room'

def test_timeout_uses_cheapest_selectable_then_stable_id():
    rows = [SimpleNamespace(person_id='c', fee_usd=1, selectable=False),
            SimpleNamespace(person_id='b', fee_usd=2, selectable=True),
            SimpleNamespace(person_id='a', fee_usd=2, selectable=True)]
    assert timeout_choice(rows).person_id == 'a'
    with pytest.raises(DraftProblem): timeout_choice(rows[:1])

@pytest.mark.parametrize('change', [{'turn_seconds':29},{'turn_seconds':181},{'turn_seconds':True},
    {'seed':'injected'},{'invite_code':'guessable'},{'host_id':str(uuid4())},{'fee_usd':0}])
def test_room_create_contract_rejects_bad_inputs(change):
    data=dict(request_id=uuid4(),genre_id='thriller',tier='blockbuster',invite_code='a'*43)
    with pytest.raises(ValidationError):w.CreateRoom(**(data|change))

def test_invite_is_redacted_but_changes_fingerprint():
    body=w.CreateRoom(request_id=uuid4(),genre_id='thriller',tier='blockbuster',invite_code='a'*43)
    assert 'a'*43 not in body.model_dump_json()
    assert service.digest('create',body)!=service.digest('create',body.model_copy(update={'invite_code':w.JoinRoom(request_id=uuid4(),invite_code='b'*43).invite_code}))

@pytest.mark.parametrize('method,suffix', [('get',''),('post','/join'),('post','/start'),('post','/picks'),('post','/cancel')])
def test_private_rooms_require_bearer_and_no_store(method,suffix):
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        response=getattr(client,method)('/api/v1/rooms/'+str(uuid4())+suffix)
        assert response.status_code==401
        assert response.headers['cache-control']=='no-store'

@pytest.mark.parametrize('origin,query', [('https://evil.example',''),('http://localhost:5173','?token=secret'),(None,'')])
def test_socket_rejects_origin_or_url_credentials(origin,query):
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/api/v1/rooms/'+str(uuid4())+'/live'+query,headers={'origin':origin} if origin else {}):pass

@pytest.mark.parametrize('frame', ['{}','[]','null','{','{"token":3}','{"token":"short"}','x'*257])
def test_socket_rejects_invalid_first_frame(frame):
    with TestClient(create_app(settings(),FakeDatabase())) as client:
        with client.websocket_connect('/api/v1/rooms/'+str(uuid4())+'/live',headers={'origin':'http://localhost:5173'}) as ws:
            ws.send_text(frame)
            with pytest.raises(WebSocketDisconnect):ws.receive_json()

def test_socket_authenticates_every_snapshot_and_disconnects_revoked_token(monkeypatch):
    db=FakeDatabase();db.engine=object();seen=[]
    def read(engine,token,room_id):
        seen.append(token)
        if len(seen)>1:raise DraftProblem(401,'invalid_session','Expired')
        return {'room_id':str(room_id),'revision':3}
    monkeypatch.setattr(service,'read',read)
    with TestClient(create_app(settings(),db)) as client:
        with client.websocket_connect('/api/v1/rooms/'+str(uuid4())+'/live',headers={'origin':'http://localhost:5173'}) as ws:
            ws.send_json({'token':'a'*43})
            assert ws.receive_json()['room']['revision']==3
            with pytest.raises(WebSocketDisconnect):ws.receive_json()
    assert seen==['a'*43,'a'*43]
