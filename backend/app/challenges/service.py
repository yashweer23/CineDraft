from uuid import UUID
import secrets,re
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import models as m,contracts as w
from app.accounts.service import authorize as account_authorize,Principal,now
from app.drafting.auth import authorize
from app.drafting import service as drafts
from app.drafting.catalog import checked_catalog
from app.drafting.errors import DraftProblem
from app.repository import canonical_hash
from app.challenges.policy import POLICY,window,phase,commitment
from app.simulation.engine import MANIFEST_HASH


def get(s,key):
    c=s.get(m.DailyChallenge,key)
    if c is None:raise DraftProblem(404,'challenge_not_found','Challenge not found.')
    if canonical_hash(c.configuration)!=c.config_hash or commitment(c.seed)!=c.seed_commitment:raise DraftProblem(503,'challenge_integrity','Challenge integrity check failed.')
    return c

def public(c,time):
    return dict(challenge_id=c.id,opens_at=c.opens_at,closes_at=c.closes_at,timezone=c.timezone,status=phase(c.opens_at,c.closes_at,time),genre_id=c.genre_id,tier=c.tier,catalog_id=c.catalog_id,config_hash=c.config_hash,seed_commitment=c.seed_commitment,configuration=c.configuration,results_hidden=time<c.closes_at,synthetic=c.configuration['synthetic'])

def open_now(s,c):
    if phase(c.opens_at,c.closes_at,now(s))!='open':raise DraftProblem(409,'challenge_not_open','This challenge is not open. Existing history remains readable.')

def publish(engine,key,catalog_id,day,zone,genre,tier,*,dry_run=False):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',key):raise ValueError('Use a 1–80 character lowercase challenge ID.')
    # Validate standard genre/tier even for direct operator calls.
    w.CreateDraftRequest(request_id=UUID(int=0),genre_id=genre,tier=tier)
    opens,closes=window(day,zone)
    with Session(engine) as s,s.begin():
        c=checked_catalog(s,catalog_id)
        if not any(t['tier']==tier and t['enabled'] for t in c.configuration['tiers']):raise ValueError('The pinned catalog cannot complete this budget tier.')
        config=dict(policy=POLICY,local_date=day.isoformat(),timezone=zone,opens_at=opens.isoformat(),closes_at=closes.isoformat(),genre_id=genre,tier=tier,versions=drafts.versions(s,c).model_dump(mode='json'),engine_manifest_hash=MANIFEST_HASH,synthetic=c.configuration['source']=='fixture')
        old=s.get(m.DailyChallenge,key)
        if old:
            if old.config_hash!=canonical_hash(config) or old.configuration!=config:raise ValueError('Challenge ID already belongs to a different immutable configuration.')
            return {'created':False,'challenge':public(get(s,key),now(s))}
        if closes<=now(s):raise ValueError('Cannot publish an already closed challenge.')
        if dry_run:return {'dry_run':True,'configuration':config,'config_hash':canonical_hash(config)}
        seed=secrets.token_hex(32);row=m.DailyChallenge(id=key,catalog_id=c.id,genre_id=genre,tier=tier,opens_at=opens,closes_at=closes,timezone=zone,configuration=config,config_hash=canonical_hash(config),seed=seed,seed_commitment=commitment(seed))
        s.add(row);s.flush();return {'created':True,'challenge':public(row,now(s))}

def listing(engine,limit=20,offset=0):
    with Session(engine) as s:
        time=now(s);rows=s.scalars(select(m.DailyChallenge).order_by(m.DailyChallenge.opens_at.desc(),m.DailyChallenge.id).offset(offset).limit(limit+1)).all()
        return {'items':[public(get(s,c.id),time) for c in rows[:limit]],'next_offset':offset+limit if len(rows)>limit else None}

def detail(engine,key):
    with Session(engine) as s:return public(get(s,key),now(s))

def begin(engine,token,key,body):
    with Session(engine) as s,s.begin():
        owner=account_authorize(s,token,exclusive=True);c=get(s,key)
        prior=s.scalar(select(m.ChallengeAttempt).where(m.ChallengeAttempt.account_id==owner.account_id,m.ChallengeAttempt.request_id==body.request_id))
        if prior:
            if prior.challenge_id!=key:raise DraftProblem(409,'idempotency_conflict','Request ID belongs to a different challenge.')
            return s.get(m.DraftRuntime,prior.draft_id).creation_response
        previous=s.scalar(select(m.ChallengeAttempt).where(m.ChallengeAttempt.challenge_id==key,m.ChallengeAttempt.account_id==owner.account_id))
        if previous:raise DraftProblem(409,'attempt_exists','Your one attempt already exists. Open it from your saved films or challenge panel.')
        open_now(s,c)
        if c.configuration['policy']!=POLICY or c.configuration['engine_manifest_hash']!=MANIFEST_HASH:raise DraftProblem(503,'unsupported_challenge','Challenge policy/engine is unsupported by this build.')
        catalog=checked_catalog(s,c.catalog_id)
        if drafts.versions(s,catalog).model_dump(mode='json')!=c.configuration['versions']:raise DraftProblem(503,'challenge_integrity','The pinned catalog version bundle differs.')
        collision=s.scalar(select(m.DraftRuntime).where(m.DraftRuntime.session_id==owner.id,m.DraftRuntime.creation_request_id==body.request_id))
        if collision:raise DraftProblem(409,'idempotency_conflict','Request ID already belongs to another film.')
        request=w.CreateDraftRequest(request_id=body.request_id,genre_id=c.genre_id,tier=c.tier)
        value=drafts.create_in_session(s,owner,request,catalog_id=c.catalog_id,seed=c.seed)
        s.add(m.ChallengeAttempt(draft_id=UUID(value['draft_id']),challenge_id=key,account_id=owner.account_id,request_id=body.request_id));s.flush()
        open_now(s,c)  # Deadline may have passed while allocating offers.
        return value

def mine(engine,token,key):
    with Session(engine) as s,s.begin():
        owner=account_authorize(s,token);get(s,key)
        row=s.scalar(select(m.ChallengeAttempt).where(m.ChallengeAttempt.account_id==owner.account_id,m.ChallengeAttempt.challenge_id==key))
        return {'draft_id':str(row.draft_id) if row else None}

def guard_action(s,draft_id,command):
    a=s.get(m.ChallengeAttempt,draft_id)
    if a and command!='abandon':open_now(s,get(s,a.challenge_id))

def finish(s,draft_id,value,output_hash):
    a=s.get(m.ChallengeAttempt,draft_id)
    if not a:return
    c=get(s,a.challenge_id);open_now(s,c)
    s.add(m.ChallengeSubmission(draft_id=draft_id,challenge_id=c.id,account_id=a.account_id,output_hash=output_hash,studio_score=value.studio_score,profit_usd=value.profit_usd));s.flush()

def guard_result(s,draft_id):
    a=s.get(m.ChallengeAttempt,draft_id)
    if a and now(s)<get(s,a.challenge_id).closes_at:raise DraftProblem(423,'challenge_results_hidden','Challenge reports and seeds remain hidden until the closing time.')

def context(engine,token,draft_id):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);drafts.owned(s,owner,draft_id)
        a=s.get(m.ChallengeAttempt,draft_id)
        return {'challenge':public(get(s,a.challenge_id),now(s)) if a else None,'submitted':s.get(m.ChallengeSubmission,draft_id) is not None}

def leaderboard(engine,key,limit=20,offset=0):
    with Session(engine) as s:
        c=get(s,key);time=now(s);info=public(c,time)
        if time<c.closes_at:return dict(challenge=info,items=[],next_offset=None,message='Rankings and release reports unlock when this challenge closes.')
        rows=s.execute(select(m.ChallengeSubmission,m.Account.username).join(m.Account,m.Account.id==m.ChallengeSubmission.account_id).where(m.ChallengeSubmission.challenge_id==key).order_by(m.ChallengeSubmission.studio_score.desc(),m.ChallengeSubmission.profit_usd.desc(),m.ChallengeSubmission.submitted_at,m.ChallengeSubmission.draft_id).offset(offset).limit(limit+1)).all()
        return dict(challenge=info,items=[dict(rank=offset+i+1,username=name,studio_score=r.studio_score,profit_usd=r.profit_usd,submitted_at=r.submitted_at,output_hash=r.output_hash) for i,(r,name) in enumerate(rows[:limit])],next_offset=offset+limit if len(rows)>limit else None,message='Studio score, then profit, then earlier submission, then draft ID. Only this pinned challenge is ranked.')

def audit(engine,key):
    with Session(engine) as s:
        c=get(s,key);time=now(s)
        if time<c.closes_at:raise DraftProblem(423,'challenge_results_hidden','The seed is revealed after this challenge closes.')
        return {'challenge':public(c,time),'seed':c.seed,'seed_commitment':c.seed_commitment,'commitment_algorithm':'sha256 of the ASCII hex seed'}
