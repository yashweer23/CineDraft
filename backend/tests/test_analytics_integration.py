"""Real PostgreSQL + SQLite boundaries. Requires the dedicated test database."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from alembic import command
from sqlalchemy import text,select,func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models as m
from app.analytics import service
from app.analytics.mart import open_mart,ingest,report
from app.analytics.schemas import ReplayRequest
from app.drafting import auth,service as drafts
from app.drafting.errors import DraftProblem
from app.accounts import service as accounts,schemas as aw
from app.simulation import service as releases
from test_persistence import database
from test_draft_integration import game,complete,action
from test_simulation_integration import finalized,release_body
from test_whatif_integration import released
from test_phase10_integration import competition,account
from test_draft_concurrency import committed_game
pytestmark=pytest.mark.integration

def test_export_then_incremental_reimport_and_unchanged_official_score(game):
    conn,t,d=game;k=UUID(d['draft_id']);db=open_mart();early=service.export(conn,t,k);assert len(early.events)==1;ingest(db,early,'internal')
    d=action(conn,t,complete(conn,t,d),'finalize');releases.release(conn,t,k,'release',release_body(d));x=service.export(conn,t,k);ingest(db,x,'internal');assert ingest(db,x,'internal')['new_events']==0
    res=report(db,group='internal',as_of=x.captured);assert res['overview'][0]['completed']==1 and res['trace'][0]['official_score']==releases.result(conn,t,k)['result']['studio_score'];db.close()

def test_replay_same_request_returns_one_child_without_changing_parent(released,database):
    c,t,d=released;k=UUID(d['draft_id']);b=ReplayRequest(request_id=uuid4());p=service.replay(c,t,k,b);assert p==service.replay(c,t,k,b) and p['draft_id']!=d['draft_id'] and p['revision']==0 and p['versions']==d['versions']
    assert drafts.read(c,t,k)==d and service.export(c,t,UUID(p['draft_id'])).events[0].kind=='replay_start'
    with Session(c) as s:assert s.get(m.Draft,k).seed!=s.get(m.Draft,UUID(p['draft_id'])).seed and s.scalar(select(func.count()).select_from(m.DraftReplay))==1
    with pytest.raises(IntegrityError),c.begin_nested():command.downgrade(database[1],'0007_phase11')

def test_foreign_owner_cannot_export_or_replay_and_claim_retains_access(released):
    c,t,d=released;k=UUID(d['draft_id']);other=auth.create_session(c)['access_token'];b=ReplayRequest(request_id=uuid4());prior=service.replay(c,t,k,b)
    for op in [lambda:service.export(c,other,k),lambda:service.replay(c,other,k,b)]:
        with pytest.raises(DraftProblem) as e:op()
        assert e.value.status==404
    a=account(c);accounts.claim_guest(c,a['access_token'],aw.Claim(guest_token=t));assert service.replay(c,a['access_token'],k,b)==prior
    assert service.export(c,a['access_token'],k).origin=='owner_export'
    with pytest.raises(DraftProblem) as e:service.export(c,t,k)
    assert e.value.status==401

def test_running_challenge_has_no_export_or_replay(competition):
    c,a,d,_=competition;k=UUID(d['draft_id']);t=a['access_token']
    for op in [lambda:service.export(c,t,k),lambda:service.replay(c,t,k,ReplayRequest(request_id=uuid4()))]:
        with pytest.raises(DraftProblem) as e:op()
        assert e.value.status==423

def test_failed_link_write_rolls_back_child_creation(released):
    c,t,d=released;b=ReplayRequest(request_id=uuid4());k=UUID(d['draft_id']);before=len(drafts.list_drafts(c,t,20)['items']);c.execute(text("CREATE FUNCTION fail_replay_for_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"));c.execute(text('CREATE TRIGGER fail_link BEFORE INSERT ON draft_replays FOR EACH ROW EXECUTE FUNCTION fail_replay_for_test()'))
    with pytest.raises(IntegrityError):service.replay(c,t,k,b)
    assert len(drafts.list_drafts(c,t,20)['items'])==before;c.execute(text('DROP TRIGGER fail_link ON draft_replays'));service.replay(c,t,k,b);assert len(drafts.list_drafts(c,t,20)['items'])==before+1

def test_concurrent_identical_replays_are_one_start(committed_game):
    c,t,d=committed_game;d=action(c,t,complete(c,t,d),'finalize');k=UUID(d['draft_id']);releases.release(c,t,k,'release',release_body(d));b=ReplayRequest(request_id=uuid4());barrier=Barrier(2)
    def run():barrier.wait(timeout=10);return service.replay(c,t,k,b)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run) for _ in range(2)];first,second=[f.result(timeout=20) for f in futures]
    assert first==second
    with Session(c) as s:assert s.scalar(select(func.count()).select_from(m.DraftReplay))==1
