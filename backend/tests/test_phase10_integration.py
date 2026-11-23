"""Real PostgreSQL account/ownership/competition checks; never run against SQLite."""
from datetime import datetime,timezone,timedelta
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from alembic import command
from app import models as m,contracts as w
from app.accounts import service as accounts,schemas as aw,security
from app.challenges import service as challenges,schemas as cw
from app.drafting import service as drafts,auth
from app.simulation import service as releases
from app.drafting.errors import DraftProblem
from test_persistence import database
from test_draft_integration import seed,game,complete,action,pick_body
from test_simulation_integration import release_body
pytestmark=pytest.mark.integration
PASSWORD='private studio passphrase!'

def account(c,name='studio_one',ip='127.0.0.1'):
    return accounts.register(c,aw.Registration(username=name,password=PASSWORD),ip)

def publish(c,key='today',day=None):
    with Session(c) as s:today=accounts.now(s).date()
    return challenges.publish(c,key,'draft-catalog:draft-v1',day or today,'UTC','drama','blockbuster')

@pytest.fixture
def competition(database):
    c=database[0];seed(c);a=account(c);publish(c)
    body=cw.Begin(request_id=uuid4());d=challenges.begin(c,a['access_token'],'today',body)
    return c,a,d,body

def test_login_password_reset_logout_and_stable_film_ownership(game):
    c,guest,d=game;a=account(c);token=a['access_token']
    assert len(token)==48 and accounts.me(c,token)['username']=='studio_one'
    claimed=accounts.claim_guest(c,token,aw.Claim(guest_token=guest));assert claimed['films']==1
    assert accounts.claim_guest(c,token,aw.Claim(guest_token=guest))==claimed
    assert drafts.read(c,token,UUID(d['draft_id']))==d
    with pytest.raises(DraftProblem) as error:drafts.read(c,guest,UUID(d['draft_id']))
    assert error.value.status==401
    b=account(c,'studio_two','different-ip')
    with pytest.raises(DraftProblem) as error:accounts.claim_guest(c,b['access_token'],aw.Claim(guest_token=guest))
    assert error.value.code=='guest_already_claimed'
    with pytest.raises(DraftProblem) as error:drafts.read(c,b['access_token'],UUID(d['draft_id']))
    assert error.value.status==404
    signed=accounts.login(c,aw.Credentials(username='studio_one',password=PASSWORD),'login-ip')
    accounts.logout(c,token)
    with pytest.raises(DraftProblem):accounts.me(c,token)
    new='another lengthy passphrase!'
    accounts.change_password(c,signed['access_token'],aw.PasswordChange(current_password=PASSWORD,new_password=new))
    with pytest.raises(DraftProblem):accounts.me(c,signed['access_token'])
    with pytest.raises(DraftProblem):accounts.login(c,aw.Credentials(username='studio_one',password=PASSWORD),'login-ip')
    fresh=accounts.login(c,aw.Credentials(username='studio_one',password=new),'login-ip')
    assert drafts.read(c,fresh['access_token'],UUID(d['draft_id']))==d
    # A canonical account owner is an unusable guest identity; it can still create new films.
    newdraft=drafts.create(c,fresh['access_token'],w.CreateDraftRequest(request_id=uuid4(),genre_id='comedy',tier='blockbuster'))
    assert newdraft['genre_id']=='comedy'
    accounts.reset_password(c,'studio_one',PASSWORD)
    with pytest.raises(DraftProblem):accounts.me(c,fresh['access_token'])
    with Session(c) as s:
        row=s.get(m.Account,a['account']['account_id']);assert security.verify_password(PASSWORD,row.password_hash)
        assert token not in str(s.scalars(select(m.AccountSession.token_hash)).all())

def test_auth_throttles_survive_failed_login_and_are_per_username(database):
    c=database[0]
    for i in range(10):
        with pytest.raises(DraftProblem) as error:accounts.login(c,aw.Credentials(username='unknown_user',password=PASSWORD),'ip-'+str(i))
        assert error.value.code=='invalid_credentials'
    with pytest.raises(DraftProblem) as error:accounts.login(c,aw.Credentials(username='unknown_user',password=PASSWORD),'a-new-ip')
    assert error.value.status==429
    with Session(c) as s:
        rows=s.scalars(select(m.AuthThrottle)).all();assert len(rows)==12
        assert all('unknown_user' not in row.bucket and 'a-new-ip' not in row.bucket for row in rows)

def test_duplicate_username_and_guest_claim_proof(game):
    c,guest,d=game;a=account(c)
    with pytest.raises(DraftProblem) as error:account(c,'STUDIO_ONE')
    assert error.value.code=='account_unavailable'
    with pytest.raises(DraftProblem):accounts.claim_guest(c,a['access_token'],aw.Claim(guest_token='z'*43))
    auth.revoke_session(c,guest)
    with pytest.raises(DraftProblem):accounts.claim_guest(c,a['access_token'],aw.Claim(guest_token=guest))

def test_one_attempt_exact_replay_and_identical_offer_stream(competition):
    c,a,d,body=competition;t=a['access_token']
    assert challenges.begin(c,t,'today',body)==d
    assert challenges.mine(c,t,'today')['draft_id']==d['draft_id']
    with pytest.raises(DraftProblem) as error:challenges.begin(c,t,'today',cw.Begin(request_id=uuid4()))
    assert error.value.code=='attempt_exists'
    b=account(c,'studio_two','second-ip');other=challenges.begin(c,b['access_token'],'today',cw.Begin(request_id=uuid4()))
    assert other['current_offer']['candidates']==d['current_offer']['candidates']
    assert other['versions']==d['versions']
    with Session(c) as s:
        first=s.get(m.Draft,UUID(d['draft_id']));second=s.get(m.Draft,UUID(other['draft_id']))
        assert first.seed==second.seed==s.get(m.DailyChallenge,'today').seed
    action(c,t,d,'abandon')
    with pytest.raises(DraftProblem) as error:challenges.begin(c,t,'today',cw.Begin(request_id=uuid4()))
    assert error.value.code=='attempt_exists'

def test_guest_cannot_enter_and_publishing_is_idempotent(competition):
    c,a,d,body=competition
    with pytest.raises(DraftProblem) as error:challenges.begin(c,auth.create_session(c)['access_token'],'today',body)
    assert error.value.status==401
    assert not publish(c)['created']
    with Session(c) as s:today=accounts.now(s).date()
    with pytest.raises(ValueError):challenges.publish(c,'today','draft-catalog:draft-v1',today,'UTC','comedy','blockbuster')
    future=publish(c,'tomorrow',today+timedelta(days=1))
    assert future['challenge']['status']=='scheduled'
    with pytest.raises(DraftProblem) as error:challenges.begin(c,a['access_token'],'tomorrow',cw.Begin(request_id=uuid4()))
    assert error.value.code=='challenge_not_open'

def test_submission_embargo_private_result_and_seed_audit(competition,monkeypatch):
    c,a,d,creation=competition;t=a['access_token'];d=action(c,t,complete(c,t,d),'finalize');body=release_body(d)
    receipt=releases.release(c,t,UUID(d['draft_id']),'release',body)
    assert challenges.context(c,t,UUID(d['draft_id']))['submitted']
    assert challenges.leaderboard(c,'today')['items']==[]
    for call in (lambda:releases.result(c,t,UUID(d['draft_id'])),lambda:challenges.audit(c,'today')):
        with pytest.raises(DraftProblem) as error:call()
        assert error.value.status==423
    with Session(c) as s:
        close=s.get(m.DailyChallenge,'today').closes_at;seed_value=s.get(m.DailyChallenge,'today').seed
        row=s.get(m.ChallengeSubmission,UUID(d['draft_id']));result=s.get(m.Result,UUID(d['draft_id']))
        assert row.output_hash==result.output_hash and row.studio_score==result.outputs['studio_score']
        assert row.profit_usd==result.outputs['profit_usd'] and row.submitted_at<close
    assert seed_value not in str(receipt)
    # Advance only the application read clock; direct SQL deadline guards are tested separately.
    monkeypatch.setattr(challenges,'now',lambda s:close)
    ranking=challenges.leaderboard(c,'today');assert ranking['items'][0]['username']=='studio_one'
    assert releases.result(c,t,UUID(d['draft_id']))['result']['reproducibility']['seed']==seed_value
    assert challenges.audit(c,'today')['seed']==seed_value
    assert releases.release(c,t,UUID(d['draft_id']),'release',body)==receipt
    assert challenges.begin(c,t,'today',creation)['revision']==0
    with pytest.raises(DraftProblem) as error:releases.release(c,t,UUID(d['draft_id']),'retry_simulation',release_body(receipt['draft']))
    assert error.value.code=='challenge_not_open'

@pytest.mark.parametrize('table',['challenge_submissions','action_records'])
def test_submission_failure_rolls_back_entire_release(competition,table):
    c,a,d,_=competition;t=a['access_token'];d=action(c,t,complete(c,t,d),'finalize');body=release_body(d)
    c.execute(text("CREATE FUNCTION fail_phase10() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text(f'CREATE TRIGGER fail_phase10 BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_phase10()'))
    with pytest.raises(IntegrityError):releases.release(c,t,UUID(d['draft_id']),'release',body)
    assert drafts.read(c,t,UUID(d['draft_id']))==d
    with Session(c) as s:
        for model in (m.Result,m.SimulationAttempt,m.ChallengeSubmission):assert s.scalar(select(func.count()).select_from(model))==0
    c.execute(text(f'DROP TRIGGER fail_phase10 ON {table}'))
    releases.release(c,t,UUID(d['draft_id']),'release',body)
    with Session(c) as s:assert s.scalar(select(func.count()).select_from(m.ChallengeSubmission))==1

def test_immutable_identity_history_and_guarded_downgrade(competition,database):
    c,a,d,_=competition
    for sql in ("UPDATE accounts SET username='changed'","DELETE FROM account_ownership","UPDATE account_sessions SET expires_at=expires_at+interval '1 year'","UPDATE daily_challenges SET seed=repeat('a',64)","DELETE FROM challenge_attempts"):
        with pytest.raises(IntegrityError),c.begin_nested():c.execute(text(sql))
    with pytest.raises(IntegrityError),c.begin_nested():command.downgrade(database[1],'0005_phase8')

def test_closed_challenge_cannot_accept_new_direct_attempt_or_action(competition):
    c,a,d,body=competition
    # Isolated test fixture only: move the existing window into the past to test DB-clock guards.
    c.execute(text('ALTER TABLE daily_challenges DISABLE TRIGGER immutable_row'))
    c.execute(text("UPDATE daily_challenges SET opens_at=clock_timestamp()-interval '2 days',closes_at=clock_timestamp()-interval '1 day'"))
    c.execute(text('ALTER TABLE daily_challenges ENABLE TRIGGER immutable_row'))
    with pytest.raises(IntegrityError),c.begin_nested():
        c.execute(text("INSERT INTO action_records(id,draft_id,command,request_id,body_hash,request_body,response_body,response_status,revision_before,revision_after) VALUES (:id,:draft,'pick',:request,repeat('a',64),'{}','{}',200,0,1)"),dict(id=uuid4(),draft=UUID(d['draft_id']),request=uuid4()))
    b=account(c,'other_studio','other-ip')
    with pytest.raises(DraftProblem) as error:challenges.begin(c,b['access_token'],'today',cw.Begin(request_id=uuid4()))
    assert error.value.code=='challenge_not_open'

def test_rank_ties_paginate_and_new_active_catalog_does_not_repin(competition,monkeypatch):
    from app.drafting.catalog import prepare
    c,a,first,_=competition;other=account(c,'studio_two','second-ip')
    prepare(c,'pricing:draft-v1','graph:draft-v1','new-active',activate=True)
    second=challenges.begin(c,other['access_token'],'today',cw.Begin(request_id=uuid4()))
    assert second['versions']==first['versions']
    scores=[]
    for owner,d in [(a,first),(other,second)]:
        t=owner['access_token'];d=action(c,t,complete(c,t,d),'finalize');releases.release(c,t,UUID(d['draft_id']),'release',release_body(d))
        with Session(c) as s:r=s.get(m.ChallengeSubmission,UUID(d['draft_id']));scores.append((r.studio_score,r.profit_usd))
    assert scores[0]==scores[1]
    with Session(c) as s:close=s.get(m.DailyChallenge,'today').closes_at
    monkeypatch.setattr(challenges,'now',lambda s:close)
    page=challenges.leaderboard(c,'today',limit=1);assert page['items'][0]['username']=='studio_one' and page['next_offset']==1
    page=challenges.leaderboard(c,'today',limit=1,offset=1);assert page['items'][0]['username']=='studio_two' and page['items'][0]['rank']==2 and page['next_offset'] is None

def test_database_rejects_seed_mismatch_and_expired_attempts(competition):
    c,a,d,_=competition
    # A fresh practice draft has the same catalog but a different server-generated seed.
    t=a['access_token'];request=w.CreateDraftRequest(request_id=uuid4(),genre_id='drama',tier='blockbuster');practice=drafts.create(c,t,request)
    with Session(c) as s:
        challenge=s.get(m.DailyChallenge,'today')
        columns={column.name:getattr(challenge,column.name) for column in m.DailyChallenge.__table__.columns}
    for key,expired in [('seed-mismatch',False),('expired',True)]:
        values=dict(columns,id=key)
        if expired:
            with Session(c) as s:dbtime=accounts.now(s);values.update(opens_at=dbtime-timedelta(days=2),closes_at=dbtime-timedelta(days=1),seed=s.get(m.Draft,UUID(practice['draft_id'])).seed)
        with Session(c) as s,s.begin():s.add(m.DailyChallenge(**values))
        with pytest.raises(IntegrityError),c.begin_nested():
            with Session(c) as s,s.begin():s.add(m.ChallengeAttempt(draft_id=UUID(practice['draft_id']),challenge_id=key,account_id=a['account']['account_id'],request_id=request.request_id));s.flush()
