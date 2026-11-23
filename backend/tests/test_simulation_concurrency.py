from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from app.simulation import service
from app.drafting.errors import DraftProblem
from test_draft_concurrency import committed_game
from test_draft_integration import complete,action
from test_simulation_integration import release_body,counts
pytestmark=pytest.mark.integration


@pytest.mark.parametrize('same_request',[True,False])
def test_concurrent_releases_save_exactly_one_result_and_attempt(committed_game,same_request):
    engine,t,d=committed_game;d=complete(engine,t,d);d=action(engine,t,d,'finalize')
    first=release_body(d);second=first if same_request else first.model_copy(update={'request_id':uuid4()});barrier=Barrier(2)
    def submit(body):
        barrier.wait(timeout=10)
        try:return service.release(engine,t,UUID(d['draft_id']),'release',body)
        except DraftProblem as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(submit,b) for b in (first,second)];responses=[f.result(timeout=20) for f in futures]
    if same_request:assert responses[0]==responses[1] and isinstance(responses[0],dict)
    else:assert sum(isinstance(r,dict) for r in responses)==1 and 'stale_revision' in responses
    assert counts(engine)==(1,1)
    assert service.status(engine,t,UUID(d['draft_id']))['status']=='results_available'
