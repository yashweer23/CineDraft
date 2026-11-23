"""Real PostgreSQL only: use the normal isolated migration fixture."""
from datetime import timedelta
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import contracts as c, models as m
from app.drafting import auth,service as solo
from app.drafting.errors import DraftProblem
from app.rooms import service as rooms,schemas as w
from test_persistence import database
from test_draft_integration import seed
pytestmark=pytest.mark.integration

@pytest.fixture
def room_game(database):
    engine=database[0];seed(engine)
    a,b,x=[auth.create_session(engine)['access_token'] for _ in range(3)]
    body=w.CreateRoom(request_id=uuid4(),genre_id='drama',tier='blockbuster',invite_code='a'*43,turn_seconds=30)
    room=rooms.create(engine,a,body)
    return engine,a,b,x,body,room

def join_start(game):
    e,a,b,x,body,room=game;id=UUID(room['room_id'])
    joined=rooms.join(e,b,id,w.JoinRoom(request_id=uuid4(),invite_code='a'*43))
    active=rooms.command(e,a,id,'start',c.MutationRequest(request_id=uuid4(),expected_revision=joined['revision']))
    return id,active

def pick(room):
    card=next(c for c in room['draft']['current_offer']['candidates'] if c['selectable'])
    return w.RoomPick(request_id=uuid4(),expected_revision=room['revision'],offer_id=room['draft']['current_offer']['offer_id'],person_id=card['card']['person_id'])

def test_create_join_replay_and_nonmember_boundary(room_game):
    e,a,b,x,body,room=room_game;id=UUID(room['room_id'])
    assert rooms.create(e,a,body)==room
    with pytest.raises(DraftProblem):rooms.create(e,a,body.model_copy(update={'turn_seconds':60}))
    with pytest.raises(DraftProblem) as err:rooms.read(e,x,id)
    assert err.value.status==404
    with pytest.raises(DraftProblem):rooms.join(e,b,id,w.JoinRoom(request_id=uuid4(),invite_code='b'*43))
    with pytest.raises(DraftProblem):rooms.join(e,a,id,w.JoinRoom(request_id=uuid4(),invite_code='a'*43))
    request=w.JoinRoom(request_id=uuid4(),invite_code='a'*43)
    first=rooms.join(e,b,id,request)
    assert first['seat']==1 and first['revision']==1
    assert rooms.join(e,b,id,request)==first
    with pytest.raises(DraftProblem):rooms.join(e,x,id,w.JoinRoom(request_id=uuid4(),invite_code='a'*43))

def test_complete_eight_alternating_picks_freezes_one_shared_film(room_game):
    e,a,b,x,_,_=room_game;id,state=join_start(room_game)
    for turn in range(8):
        body=pick(state);owner=(a,b)[turn%2]
        with pytest.raises(DraftProblem) as err:rooms.command(e,(b,a)[turn%2],id,'pick',body)
        assert err.value.code=='not_your_turn'
        first=rooms.command(e,owner,id,'pick',body)
        assert rooms.command(e,owner,id,'pick',body)==first
        state=rooms.read(e,a,id)
        assert len(state['members'])==turn+1
    assert state['state']=='complete' and state['deadline'] is None
    assert state['draft']['status']=='production_finalized'
    assert len({p['person_id'] for p in state['draft']['picks']})==8
    assert state['draft']['budget']['talent_spend_usd']==sum(p['locked_fee_usd'] for p in state['members'])
    assert solo.read(e,a,UUID(state['draft']['draft_id']))['snapshot_hash']
    with pytest.raises(DraftProblem):solo.read(e,b,UUID(state['draft']['draft_id']))
    # Replaying an old receipt cannot advance a completed room.
    assert rooms.advance_due(e)==0
    with Session(e) as s:assert s.scalar(select(func.count()).select_from(m.DraftSnapshot))==1

def test_solo_route_cannot_bypass_room_or_change_budget(room_game):
    e,a,b,x,_,_=room_game;id,room=join_start(room_game)
    body=pick(room).model_copy(update={'expected_revision':room['draft']['revision']})
    with pytest.raises(DraftProblem) as err:solo.mutate(e,a,UUID(room['draft']['draft_id']),'pick',body)
    assert err.value.code=='room_managed'
    assert rooms.read(e,a,id)['revision']==room['revision']

def test_timeout_survives_reconnect_and_advances_only_once(room_game):
    e,a,b,x,_,_=room_game;id,room=join_start(room_game)
    with Session(e) as s,s.begin():s.get(m.DraftRoom,id).deadline=rooms.now(s)-timedelta(seconds=500)
    with pytest.raises(DraftProblem) as err:rooms.command(e,a,id,'pick',pick(room))
    assert err.value.code=='turn_expired'
    assert rooms.advance_due(e)==1
    assert rooms.advance_due(e)==0
    state=rooms.read(e,b,id)
    assert len(state['members'])==1 and state['turn_seat']==1 and state['events'][0]['automatic']
    with pytest.raises(DraftProblem) as err:rooms.command(e,a,id,'pick',pick(room))
    assert err.value.code=='stale_room'

def test_host_can_cancel_and_receipts_reject_changed_body(room_game):
    e,a,b,x,_,_=room_game;id,room=join_start(room_game)
    body=c.MutationRequest(request_id=uuid4(),expected_revision=room['revision'])
    with pytest.raises(DraftProblem):rooms.command(e,b,id,'cancel',body)
    first=rooms.command(e,a,id,'cancel',body)
    assert first['state']=='cancelled' and first['draft']['status']=='abandoned'
    assert rooms.command(e,a,id,'cancel',body)==first
    with pytest.raises(DraftProblem):rooms.command(e,a,id,'start',body)
