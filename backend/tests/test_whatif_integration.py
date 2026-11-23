"""PostgreSQL-only ownership, budgets, immutable history, retry and rollback checks."""
from uuid import UUID,uuid4
from decimal import Decimal
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from alembic import command
from app import models as m
from app.whatif import service
from app.whatif.schemas import CompareRequest
from app.whatif.engine import compare
from app.drafting import service as drafts,auth
from app.drafting.errors import DraftProblem
from app.simulation import service as releases
from app.repository import canonical_hash
from test_persistence import database
from test_draft_integration import game,complete,action
from test_simulation_integration import finalized,release_body
pytestmark=pytest.mark.integration

@pytest.fixture
def released(finalized):
    c,t,d=finalized;d=releases.release(c,t,UUID(d['draft_id']),'release',release_body(d))['draft'];return c,t,d

def body(d,**fields):return CompareRequest(request_id=uuid4(),slot='director',person_id=d['picks'][0]['person_id'],**fields)
def count(c,model):
    with Session(c) as s:return s.scalar(select(func.count()).select_from(model))

def official(c,d):
    with Session(c) as s:
        result=s.get(m.Result,UUID(d['draft_id']));snapshot=s.get(m.DraftSnapshot,UUID(d['draft_id']))
        return canonical_hash(result.outputs),canonical_hash(snapshot.inputs),count(c,m.ActionRecord),count(c,m.SimulationAttempt)

def test_control_replay_cache_and_official_records_unchanged(released):
    c,t,d=released;key=UUID(d['draft_id']);before=official(c,d);b=body(d)
    first=service.create(c,t,key,b)
    assert service.create(c,t,key,b)==first
    assert service.create(c,t,key,b.model_copy(update={'request_id':uuid4()}))==first
    assert count(c,m.WhatIfAnalysis)==1 and count(c,m.WhatIfReceipt)==2
    assert drafts.read(c,t,key)==d and official(c,d)==before
    assert all(Decimal(v)==0 for metric in first['comparison']['metrics'] for v in metric['paired_delta'].values())
    assert service.read(c,t,key,UUID(first['analysis_id']))==first
    assert service.history(c,t,key)['items'][0]['unchanged']
    with Session(c) as s:
        row=s.get(m.WhatIfAnalysis,UUID(first['analysis_id']));assert compare(row.inputs)==row.outputs
        assert row.output_hash==canonical_hash(row.outputs)
    with pytest.raises(DraftProblem) as e:service.create(c,t,key,b.model_copy(update={'slot':'writer'}))
    assert e.value.code=='idempotency_conflict'

def test_replacement_uses_pinned_role_price_and_retains_original_film(released):
    c,t,d=released;key=UUID(d['draft_id']);page=service.candidates(c,t,key,'director',1)
    assert page['next_offset']==1
    choices=service.candidates(c,t,key,'director',50)['items'];chosen=next(x for x in choices if not x['is_original'] and x['selectable'])
    saved=service.create(c,t,key,body(d).model_copy(update={'person_id':UUID(chosen['card']['person_id'])}));r=saved['comparison']
    assert r['budget']['replacement_fee_usd']==chosen['card']['hiring_fee_usd']
    assert r['budget']['alternative_spend_usd']==chosen['hypothetical_spend_usd']
    assert not r['unchanged'] and r['source_input_hash']==d['snapshot_hash']
    assert drafts.read(c,t,key)==d
    with Session(c) as s:
        row=s.get(m.WhatIfAnalysis,UUID(saved['analysis_id']))
        assert len(row.inputs['alternative']['draft']['picks'])==8
        assert all(e['title']=='Synthetic Draft Film' for pair in r['explanation']['relationships'] for edge in ('before','after') for e in pair[edge]['evidence'])

def test_wrong_owner_and_missing_analysis_do_not_disclose_history(released):
    c,t,d=released;key=UUID(d['draft_id']);b=body(d);saved=service.create(c,t,key,b);other=auth.create_session(c)['access_token']
    for fn in (lambda:service.create(c,other,key,b),lambda:service.candidates(c,other,key,'director'),lambda:service.history(c,other,key),lambda:service.read(c,other,key,UUID(saved['analysis_id']))):
        with pytest.raises(DraftProblem) as e:fn()
        assert e.value.status==404
    with pytest.raises(DraftProblem) as e:service.read(c,t,key,uuid4())
    assert e.value.status==404
    auth.revoke_session(c,t)
    with pytest.raises(DraftProblem) as e:service.history(c,t,key)
    assert e.value.status==401

@pytest.mark.parametrize('mode',['duplicate','wrong_role','missing'])
def test_rejects_invalid_substitution_without_persisting(released,mode):
    c,t,d=released;key=UUID(d['draft_id']);pid=UUID(d['picks'][1]['person_id']) if mode=='duplicate' else uuid4()
    if mode=='wrong_role':pid=UUID(next(x['card']['person_id'] for x in service.candidates(c,t,key,'writer',50)['items'] if not x['is_original']))
    with pytest.raises(DraftProblem) as e:service.create(c,t,key,body(d).model_copy(update={'person_id':pid}))
    assert e.value.status==422 and count(c,m.WhatIfAnalysis)==0 and count(c,m.WhatIfReceipt)==0

def test_unreleased_film_cannot_open_lab(game):
    c,t,d=game
    with pytest.raises(DraftProblem) as e:service.history(c,t,UUID(d['draft_id']))
    assert e.value.code=='whatif_requires_release'

@pytest.mark.parametrize('table',['whatif_analyses','whatif_receipts'])
def test_failed_write_rolls_back_both_tables_and_same_request_can_retry(released,table):
    c,t,d=released;key=UUID(d['draft_id']);b=body(d);before=official(c,d)
    c.execute(text("CREATE FUNCTION fail_whatif_write() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text(f'CREATE TRIGGER fail_whatif_write BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_whatif_write()'))
    with pytest.raises(IntegrityError):service.create(c,t,key,b)
    assert count(c,m.WhatIfAnalysis)==0 and count(c,m.WhatIfReceipt)==0 and official(c,d)==before
    c.execute(text(f'DROP TRIGGER fail_whatif_write ON {table}'));service.create(c,t,key,b)
    assert count(c,m.WhatIfAnalysis)==1 and count(c,m.WhatIfReceipt)==1

def test_history_cannot_be_edited_deleted_or_downgraded(released,database):
    c,t,d=released;service.create(c,t,UUID(d['draft_id']),body(d))
    for sql in ("UPDATE whatif_analyses SET outputs='{}'::jsonb","DELETE FROM whatif_analyses","UPDATE whatif_receipts SET request_body='{}'::jsonb","DELETE FROM whatif_receipts"):
        with pytest.raises(IntegrityError),c.begin_nested():c.execute(text(sql))
    with pytest.raises(IntegrityError),c.begin_nested():command.downgrade(database[1],'0006_phase10')

from test_phase10_integration import competition,account
from app.accounts import service as accounts,schemas as aw
from app.challenges import service as challenges

def test_claim_preserves_private_analysis_and_revokes_guest_access(released):
    c,t,d=released;key=UUID(d['draft_id']);b=body(d);saved=service.create(c,t,key,b);a=account(c)
    accounts.claim_guest(c,a['access_token'],aw.Claim(guest_token=t))
    assert service.read(c,a['access_token'],key,UUID(saved['analysis_id']))==saved
    assert service.create(c,a['access_token'],key,b)==saved
    with pytest.raises(DraftProblem) as e:service.history(c,t,key)
    assert e.value.status==401

def test_all_paths_and_direct_insert_are_embargoed_before_challenge_close(competition,monkeypatch):
    c,a,d,_=competition;t=a['access_token'];d=action(c,t,complete(c,t,d),'finalize');d=releases.release(c,t,UUID(d['draft_id']),'release',release_body(d))['draft'];key=UUID(d['draft_id']);b=body(d)
    for fn in (lambda:service.create(c,t,key,b),lambda:service.candidates(c,t,key,'director'),lambda:service.history(c,t,key),lambda:service.read(c,t,key,uuid4())):
        with pytest.raises(DraftProblem) as e:fn()
        assert e.value.status==423
    with Session(c) as s:close=s.get(m.DailyChallenge,'today').closes_at
    monkeypatch.setattr(challenges,'now',lambda s:close)
    # The app clock can advance in this test, but SQL checks the real database clock.
    assert service.candidates(c,t,key,'director')['items']
    with pytest.raises(IntegrityError):service.create(c,t,key,b)
    assert count(c,m.WhatIfAnalysis)==0 and count(c,m.WhatIfReceipt)==0
