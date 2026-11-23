"""Real PostgreSQL release, retry, immutable history and atomic persistence."""
from uuid import UUID,uuid4
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import models as m,contracts as w
from app.drafting import service as drafts,auth
from app.drafting.errors import DraftProblem
from app.repository import load_snapshot,canonical_hash
from app.simulation import service
from app.simulation.engine import simulate
from app.simulation.schemas import SimulationResult
from app.main import create_app
from test_foundation import FakeDatabase,settings
from test_persistence import database
from test_draft_integration import game,complete,action
pytestmark=pytest.mark.integration


@pytest.fixture
def finalized(game):
    c,t,d=game;d=complete(c,t,d);d=action(c,t,d,'finalize')
    return c,t,d


def release_body(d):return w.MutationRequest(request_id=uuid4(),expected_revision=d['revision'])


def counts(c):
    with Session(c) as s:
        return tuple(s.scalar(select(func.count()).select_from(model)) for model in (m.Result,m.SimulationAttempt))


def test_release_freezes_result_matches_pure_replay_and_resumes(finalized):
    c,t,d=finalized;body=release_body(d)
    response=service.release(c,t,UUID(d['draft_id']),'release',body)
    assert response['draft']['status']=='results_available' and response['draft']['revision']==d['revision']+1
    assert response['attempt']['status']=='succeeded' and response['attempt']['attempt_number']==1
    result=service.result(c,t,UUID(d['draft_id']));assert len(result['output_hash'])==64
    with Session(c) as s:
        frozen=load_snapshot(s,UUID(d['draft_id']))
        expected=SimulationResult.model_validate(simulate(frozen,d['snapshot_hash'])).model_dump(mode='json')
        assert result['result']==expected and canonical_hash(expected)==result['output_hash']
        assert s.get(m.DraftSnapshot,UUID(d['draft_id'])).input_hash==d['snapshot_hash']
        assert frozen.draft.status=='production_finalized'  # Live status changes never rewrite inputs.
    assert service.release(c,t,UUID(d['draft_id']),'release',body)==response
    assert service.status(c,t,UUID(d['draft_id']))['result_available']
    assert drafts.read(c,t,UUID(d['draft_id']))['budget']==d['budget']
    assert counts(c)==(1,1)


def test_failure_is_durable_safe_and_retry_uses_original_seed(finalized,monkeypatch,caplog):
    c,t,d=finalized;body=release_body(d)
    with Session(c) as s:frozen=load_snapshot(s,UUID(d['draft_id']))
    expected=SimulationResult.model_validate(simulate(frozen,d['snapshot_hash'])).model_dump(mode='json')
    original=service.simulate
    def fail(*args):raise RuntimeError('SECRET_PRIVATE_EXCEPTION')
    monkeypatch.setattr(service,'simulate',fail)
    failed=service.release(c,t,UUID(d['draft_id']),'release',body)
    assert failed['draft']['status']=='simulation_failed' and failed['attempt']['error_code']=='engine_error'
    assert 'SECRET_PRIVATE_EXCEPTION' not in str(failed) and 'SECRET_PRIVATE_EXCEPTION' not in caplog.text
    assert counts(c)==(0,1)
    assert service.status(c,t,UUID(d['draft_id']))['latest_attempt']['status']=='failed'
    monkeypatch.setattr(service,'simulate',original)
    retry_body=release_body(failed['draft'])
    success=service.release(c,t,UUID(d['draft_id']),'retry_simulation',retry_body)
    assert success['attempt']['attempt_number']==2 and success['draft']['status']=='results_available'
    assert service.result(c,t,UUID(d['draft_id']))['result']==expected
    assert service.release(c,t,UUID(d['draft_id']),'retry_simulation',retry_body)==success
    assert service.release(c,t,UUID(d['draft_id']),'release',body)==failed  # Original receipt remains original.
    assert counts(c)==(1,2)


@pytest.mark.parametrize('table',['results','simulation_attempts','action_records'])
def test_persistence_failure_rolls_back_result_attempt_and_state(finalized,table):
    c,t,d=finalized;body=release_body(d)
    c.execute(text("CREATE FUNCTION fail_release_write() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text(f'CREATE TRIGGER fail_release_write BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_release_write()'))
    with pytest.raises(IntegrityError):service.release(c,t,UUID(d['draft_id']),'release',body)
    assert drafts.read(c,t,UUID(d['draft_id']))==d and counts(c)==(0,0)
    c.execute(text(f'DROP TRIGGER fail_release_write ON {table}'))
    # The same request can now commit once; no new seed is produced.
    saved=service.release(c,t,UUID(d['draft_id']),'release',body)
    assert saved['attempt']['attempt_number']==1 and counts(c)==(1,1)


def test_wrong_owner_cannot_read_replay_or_mutate_release(finalized):
    c,t,d=finalized;body=release_body(d);other=auth.create_session(c)['access_token']
    service.release(c,t,UUID(d['draft_id']),'release',body)
    for operation in (lambda:service.release(c,other,UUID(d['draft_id']),'release',body),lambda:service.status(c,other,UUID(d['draft_id'])),lambda:service.result(c,other,UUID(d['draft_id']))):
        with pytest.raises(DraftProblem) as e:operation()
        assert e.value.status==404
    auth.revoke_session(c,t)
    with pytest.raises(DraftProblem) as e:service.result(c,t,UUID(d['draft_id']))
    assert e.value.status==401


def test_unfinalized_and_missing_result_are_rejected_without_mutation(game):
    c,t,d=game
    with pytest.raises(DraftProblem) as e:service.release(c,t,UUID(d['draft_id']),'release',release_body(d))
    assert e.value.code=='invalid_release_state'
    with pytest.raises(DraftProblem) as e:service.result(c,t,UUID(d['draft_id']))
    assert e.value.code=='result_not_available'
    assert drafts.read(c,t,UUID(d['draft_id']))==d and counts(c)==(0,0)


def test_stale_revision_conflicting_receipt_and_completed_retry_rejected(finalized):
    c,t,d=finalized;body=release_body(d)
    with pytest.raises(DraftProblem) as e:service.release(c,t,UUID(d['draft_id']),'release',body.model_copy(update={'expected_revision':0}))
    assert e.value.code=='stale_revision'
    saved=service.release(c,t,UUID(d['draft_id']),'release',body)
    with pytest.raises(DraftProblem) as e:service.release(c,t,UUID(d['draft_id']),'release',body.model_copy(update={'expected_revision':saved['draft']['revision']}))
    assert e.value.code=='idempotency_conflict'
    for cmd in ('release','retry_simulation'):
        with pytest.raises(DraftProblem) as e:service.release(c,t,UUID(d['draft_id']),cmd,release_body(saved['draft']))
        assert e.value.code=='invalid_release_state'
    assert counts(c)==(1,1)


def test_released_attempts_results_and_migration_history_are_protected(finalized,database):
    c,t,d=finalized;service.release(c,t,UUID(d['draft_id']),'release',release_body(d))
    for sql in ("UPDATE simulation_attempts SET status='failed'","DELETE FROM simulation_attempts","UPDATE results SET outputs='{}'::jsonb","DELETE FROM results"):
        with pytest.raises(IntegrityError),c.begin_nested():c.execute(text(sql))
    with pytest.raises(IntegrityError),c.begin_nested():command.downgrade(database[1],'0004_phase7')
    assert service.result(c,t,UUID(d['draft_id']))['result']['draft_id']==d['draft_id']


def test_http_release_receipt_result_and_owner_status(finalized):
    c,t,d=finalized;db=FakeDatabase();db.engine=c;headers={'Authorization':'Bearer '+t};base='/api/v1/drafts/'+d['draft_id']
    with TestClient(create_app(settings(),db)) as client:
        assert client.get(base+'/simulation',headers=headers).json()['latest_attempt'] is None
        response=client.post(base+'/release',headers=headers,json=release_body(d).model_dump(mode='json'))
        assert response.status_code==200,response.text
        assert response.json()['draft']['status']=='results_available'
        result=client.get(base+'/result',headers=headers)
        assert result.status_code==200,result.text
        assert result.json()['result']['schema_version']=='phase8-v1' and result.headers['cache-control']=='no-store'
        assert client.get(base+'/result').status_code==401
