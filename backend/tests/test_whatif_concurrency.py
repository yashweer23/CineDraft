from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from app import models as m
from app.whatif import service
from app.whatif.schemas import CompareRequest
from app.simulation import service as releases
from test_draft_concurrency import committed_game
from test_draft_integration import complete,action
from test_simulation_integration import release_body
pytestmark=pytest.mark.integration

@pytest.mark.parametrize('same_request',[True,False])
def test_simultaneous_comparisons_save_one_analysis(committed_game,same_request):
    c,t,d=committed_game;d=complete(c,t,d);d=action(c,t,d,'finalize');d=releases.release(c,t,UUID(d['draft_id']),'release',release_body(d))['draft']
    first=CompareRequest(request_id=uuid4(),slot='director',person_id=d['picks'][0]['person_id']);second=first if same_request else first.model_copy(update={'request_id':uuid4()});barrier=Barrier(2)
    def submit(b):barrier.wait(timeout=10);return service.create(c,t,UUID(d['draft_id']),b)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(submit,b) for b in (first,second)];results=[f.result(timeout=20) for f in futures]
    assert results[0]==results[1]
    with Session(c) as s:
        assert s.scalar(select(func.count()).select_from(m.WhatIfAnalysis))==1
        assert s.scalar(select(func.count()).select_from(m.WhatIfReceipt))==(1 if same_request else 2)
