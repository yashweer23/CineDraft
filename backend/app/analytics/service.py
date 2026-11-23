"""Project committed gameplay receipts to an allowlist; never export bearer data or raw bodies."""
from uuid import UUID,uuid5,NAMESPACE_URL
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import models as m
from app.repository import canonical_hash
from app.drafting import service as drafts
from app.drafting.auth import authorize
from app.drafting.errors import DraftProblem
from app.challenges.service import guard_result
from .schemas import Stream,ReplayBrief

def key(kind,identity):return canonical_hash(['gameplay-events-1.0',kind,str(identity)])

def replay(engine,token,draft_id,body):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token,exclusive=True);d,rt,c=drafts.owned(s,owner,draft_id,write=True);guard_result(s,draft_id)
        if d.status!='results_available' or s.get(m.Result,draft_id) is None:raise DraftProblem(422,'release_required','Release this film successfully before replaying its brief.')
        link=s.get(m.DraftReplay,(draft_id,body.request_id))
        if link:
            _,child_rt,_=drafts.owned(s,owner,link.child_id);return child_rt.creation_response
        # Distinct creation namespace and digest prevent a practice POST from aliasing this receipt.
        nonce=uuid5(NAMESPACE_URL,f'cinedraft:replay:{draft_id}:{body.request_id}')
        brief=ReplayBrief(request_id=nonce,source_id=draft_id,genre_id=d.genre_id,tier=d.tier)
        value=drafts.create_in_session(s,owner,brief,catalog_id=c.id)
        s.add(m.DraftReplay(source_id=draft_id,request_id=body.request_id,child_id=UUID(value['draft_id'])));s.flush();return value

def project(d,rt,c,actions,result,analyses,replayed,challenge,captured):
    events=[];opportunities=[];seen=set();sid=key('session',d.id)
    def offer_rows(response,at,event_key):
        o=response.get('current_offer');
        if not o or o['offer_id'] in seen:return
        seen.add(o['offer_id'])
        for candidate in o['candidates']:
            if candidate['selectable']:
                card=candidate['card'];opportunities.append(dict(kind=o['kind'],offer=key('offer',o['offer_id']),person=str(card['person_id']),name=card['name'],slot=o['slot'],at=at,event_key=event_key))
    first=key('start',d.id);events.append(dict(event_key=first,kind='replay_start' if replayed else 'start',at=d.created_at,revision=0));offer_rows(rt.creation_response,d.created_at,first)
    for a in actions:
        response=a.response_body.get('draft',a.response_body);cmd=a.command;ek=key('action',a.id)
        ev=dict(event_key=ek,kind=cmd,at=a.created_at,revision=a.revision_after)
        if cmd in ('pick','confirm_recast'):
            chosen=next(p for p in response['picks'] if p['person_id']==a.request_body['person_id'] and p['offer_id']==a.request_body['offer_id'])
            ev.update(slot=chosen['slot'],person=chosen['person_id'],offer=key('offer',chosen['offer_id']),fee=chosen['locked_fee_usd'])
        if cmd in ('release','retry_simulation'):
            ev['kind']='release' if response['status']=='results_available' else 'release_failed'
            if ev['kind']=='release':
                if result is None or result.outputs.get('schema_version')!='phase8-v1' or canonical_hash(result.outputs)!=result.output_hash:raise ValueError('Inconsistent official result.')
                ev.update(score=result.outputs['studio_score'],profit=result.outputs['profit_usd'])
        events.append(ev);offer_rows(response,a.created_at,ek)
    for row in analyses:events.append(dict(event_key=key('whatif',row.id),kind='whatif',at=row.created_at,revision=d.revision))
    return Stream(session_key=sid,started=d.created_at,captured=captured,genre=d.genre_id,tier=d.tier,catalog=c.id,rules=d.rules_id,scoring=d.scoring_id,simulation=d.simulation_version,fixture=c.configuration['source']=='fixture',mode='closed_challenge' if challenge else 'practice',total=d.total_budget_usd,allowance=d.talent_budget_usd,reserve=d.reserve_usd,events=events,opportunities=opportunities)

def export(engine,token,draft_id):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=drafts.owned(s,owner,draft_id);guard_result(s,draft_id)
        actions=s.scalars(select(m.ActionRecord).where(m.ActionRecord.draft_id==d.id).order_by(m.ActionRecord.revision_after)).all()
        comparisons=s.execute(select(m.WhatIfAnalysis.id,m.WhatIfAnalysis.created_at).where(m.WhatIfAnalysis.draft_id==d.id).order_by(m.WhatIfAnalysis.created_at,m.WhatIfAnalysis.id)).all()
        try:return project(d,rt,c,actions,s.get(m.Result,d.id),comparisons,s.scalar(select(m.DraftReplay.child_id).where(m.DraftReplay.child_id==d.id)) is not None,s.get(m.ChallengeAttempt,d.id) is not None,s.scalar(select(func.clock_timestamp())))
        except (ValueError,KeyError,StopIteration):raise DraftProblem(503,'analytics_source_error','Saved gameplay evidence is inconsistent. No export was written.') from None
