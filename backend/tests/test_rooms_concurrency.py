from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4
import pytest
from app import contracts as c
from app.drafting import auth
from app.drafting.errors import DraftProblem
from app.rooms import service as rooms,schemas as w
from test_draft_concurrency import committed_game
from test_rooms_integration import pick
pytestmark=pytest.mark.integration

@pytest.mark.parametrize('same_request',[True,False])
def test_two_connections_can_commit_only_one_room_pick(committed_game,same_request):
    engine,a,_=committed_game;b=auth.create_session(engine)['access_token']
    room=rooms.create(engine,a,w.CreateRoom(request_id=uuid4(),genre_id='drama',tier='blockbuster',invite_code='a'*43))
    id=UUID(room['room_id']);joined=rooms.join(engine,b,id,w.JoinRoom(request_id=uuid4(),invite_code='a'*43))
    state=rooms.command(engine,a,id,'start',c.MutationRequest(request_id=uuid4(),expected_revision=joined['revision']))
    first=pick(state);second=first if same_request else first.model_copy(update={'request_id':uuid4()})
    barrier=Barrier(2)
    def run(body):
        barrier.wait(timeout=10)
        try:return rooms.command(engine,a,id,'pick',body)
        except DraftProblem as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,body) for body in (first,second)]
        results=[f.result(timeout=20) for f in futures]
    if same_request:assert results[0]==results[1] and isinstance(results[0],dict)
    else:assert sum(isinstance(v,dict) for v in results)==1 and 'stale_room' in results
    assert len(rooms.read(engine,b,id)['members'])==1
