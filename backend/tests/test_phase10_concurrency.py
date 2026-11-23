"""Committed, isolated PostgreSQL schema: race claims, attempts and official releases."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import models as m
from app.accounts import service as accounts,schemas as aw
from app.challenges import service as challenges,schemas as cw
from app.simulation import service as releases
from app.drafting.errors import DraftProblem
from test_draft_concurrency import committed_game
from test_draft_integration import complete,action
from test_simulation_integration import release_body
from test_phase10_integration import account,publish
pytestmark=pytest.mark.integration

def race(function,values):
    barrier=Barrier(2)
    def go(value):
        barrier.wait(timeout=10)
        try:return function(value)
        except DraftProblem as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(go,v) for v in values]
        return [f.result(timeout=20) for f in futures]

@pytest.mark.parametrize('same_request',[True,False])
def test_one_official_attempt_under_racing_creates(committed_game,same_request):
    c,_,_=committed_game;a=account(c);publish(c);first=cw.Begin(request_id=uuid4());second=first if same_request else cw.Begin(request_id=uuid4())
    results=race(lambda body:challenges.begin(c,a['access_token'],'today',body),[first,second])
    if same_request:assert results[0]==results[1] and isinstance(results[0],dict)
    else:assert sum(isinstance(v,dict) for v in results)==1 and 'attempt_exists' in results
    with Session(c) as s:assert s.scalar(select(func.count()).select_from(m.ChallengeAttempt))==1

def test_two_accounts_cannot_claim_same_guest(committed_game):
    c,guest,_=committed_game;one=account(c);two=account(c,'other_studio','second-ip')
    results=race(lambda t:accounts.claim_guest(c,t,aw.Claim(guest_token=guest)),[one['access_token'],two['access_token']])
    assert sum(isinstance(v,dict) for v in results)==1 and 'guest_already_claimed' in results

def test_same_release_race_creates_one_official_submission(committed_game):
    c,_,_=committed_game;a=account(c);publish(c);t=a['access_token'];d=challenges.begin(c,t,'today',cw.Begin(request_id=uuid4()))
    d=action(c,t,complete(c,t,d),'finalize');body=release_body(d)
    results=race(lambda b:releases.release(c,t,UUID(d['draft_id']),'release',b),[body,body])
    assert results[0]==results[1] and isinstance(results[0],dict)
    with Session(c) as s:
        assert s.scalar(select(func.count()).select_from(m.ChallengeSubmission))==1
        assert s.scalar(select(func.count()).select_from(m.Result))==1
