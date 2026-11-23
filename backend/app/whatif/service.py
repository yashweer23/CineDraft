"""Owner-only, immutable what-if reports. All input comes from pinned local data."""
from types import SimpleNamespace
from uuid import UUID,uuid5,NAMESPACE_URL
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.domain import Slot,SLOT_ROLES
from app.repository import canonical_hash,load_snapshot
from app.drafting import service as drafts
from app.drafting.auth import authorize
from app.drafting.catalog import checked_catalog,pool_for
from app.drafting.errors import DraftProblem
from app.drafting.schemas import FrozenDraft
from app.challenges.service import guard_result
from app.simulation.engine import verify_snapshot
from app.simulation.schemas import SimulationResult
from app.whatif import schemas as w
from app.whatif.engine import MANIFEST,VERSION,project,compare


def problem(code,message,status=422):raise DraftProblem(status,code,message)

def access(s,token,draft_id,*,write=False):
    owner=authorize(s,token);d,rt,c=drafts.owned(s,owner,draft_id,write=write)
    guard_result(s,draft_id)  # Applies to every lab route, before candidate/history/result exposure.
    result=s.get(m.Result,draft_id)
    if d.status!='results_available' or result is None:problem('whatif_requires_release','Complete a successful release before opening the what-if lab.')
    try:
        frozen=load_snapshot(s,draft_id)
        if not isinstance(frozen,FrozenDraft):raise ValueError('Only phase7 inputs are supported.')
        verify_snapshot(frozen,result.input_hash)
        value=SimulationResult.model_validate(result.outputs)
        if canonical_hash(result.outputs)!=result.output_hash or value.input_hash!=result.input_hash or value.simulation_id!=result.simulation_id or value.draft_id!=d.id:raise ValueError('Result integrity mismatch.')
    except (ValueError,LookupError):problem('whatif_source_integrity','Source result or frozen production is unsupported or inconsistent.',503)
    return d,c,frozen,result

def selection(frozen,slot):return next(p for p in frozen.draft.picks if p.slot==slot)
def source_card(frozen,slot):return next(c for c in frozen.cards if c.person_id==selection(frozen,slot).person_id)

def pinned(s,c,frozen):
    c=checked_catalog(s,c.id)
    if drafts.versions(s,c)!=frozen.draft.versions:problem('whatif_catalog_integrity','The original catalog version bundle does not match the frozen film.',503)
    return pool_for(s,c.pricing_id)

def candidates(engine,token,draft_id,slot,limit=12,offset=0):
    with Session(engine) as s,s.begin():
        _,c,frozen,_=access(s,token,draft_id);pool=pinned(s,c,frozen);slot=Slot(slot);old=selection(frozen,slot)
        used={str(p.person_id) for p in frozen.draft.picks if p.slot!=slot};role=SLOT_ROLES[slot].value
        rows=sorted((p for p in pool if p.role==role and p.person_id not in used),key=lambda p:(p.fee_usd,p.person_id))
        page=rows[offset:offset+limit];cards=drafts.cards(s,c,[{'talent':p} for p in page],frozen.draft.genre_id)
        available=frozen.draft.budget.talent_remaining_usd+old.locked_fee_usd;items=[]
        for row in page:
            original=row.person_id==str(old.person_id);card=source_card(frozen,slot) if original else cards[row.person_id]
            fee=card.hiring_fee_usd;selectable=fee<=available
            items.append(dict(card=card,is_original=original,selectable=selectable,blocked_reason=None if selectable else 'Exceeds the original hiring allowance after refund.',hypothetical_spend_usd=frozen.draft.budget.talent_spend_usd-old.locked_fee_usd+fee))
        return w.Candidates(slot=slot,original=source_card(frozen,slot),available_after_refund_usd=available,items=items,next_offset=offset+limit if len(rows)>offset+limit else None).model_dump(mode='json')

def build_inputs(s,d,c,frozen,result,body):
    pool=pinned(s,c,frozen);baseline=project(frozen);old=selection(frozen,body.slot)
    if body.person_id==old.person_id:alternative=baseline.model_copy(deep=True)
    else:
        if body.person_id in {p.person_id for p in frozen.draft.picks}:problem('whatif_duplicate_person','The other seven slots must keep distinct people.')
        chosen=next((p for p in pool if p.person_id==str(body.person_id) and p.role==SLOT_ROLES[body.slot].value),None)
        if chosen is None:problem('whatif_invalid_replacement','Choose a person in this role from the original pinned catalog.')
        spend=frozen.draft.budget.talent_spend_usd-old.locked_fee_usd+chosen.fee_usd
        if spend>frozen.draft.budget.talent_budget_usd:problem('whatif_over_budget','Replacement exceeds the original hiring allowance after refund.')
        profile=s.get(m.RoleFeature,(c.feature_id,body.person_id,chosen.role))
        if profile is None:problem('whatif_catalog_integrity','Pinned role profile is missing.',503)
        card=drafts.cards(s,c,[{'talent':chosen}],frozen.draft.genre_id)[chosen.person_id]
        data=baseline.model_dump(mode='json')
        data['draft']['picks']=[dict(p,person_id=str(body.person_id),locked_fee_usd=chosen.fee_usd) if p['slot']==body.slot.value else p for p in data['draft']['picks']]
        data['draft']['budget'].update(talent_spend_usd=spend,talent_remaining_usd=frozen.draft.budget.talent_budget_usd-spend)
        data['cards']=[card.model_dump(mode='json') if x['person_id']==str(old.person_id) else x for x in data['cards']]
        data['role_features']=[dict(person_id=str(body.person_id),role=chosen.role,attributes=profile.attributes,evidence=profile.evidence) if x['person_id']==str(old.person_id) else x for x in data['role_features']]
        selections=[SimpleNamespace(slot=p['slot'],person_id=UUID(p['person_id'])) for p in data['draft']['picks']]
        data['collaborations']=drafts.frozen_collaborations(s,d,selections)
        alternative=w.Team.model_validate(data)
    ids={UUID(e['movie_id']) for team in (baseline,alternative) for edge in team.collaborations for e in edge['evidence']}
    movies={str(row.movie_id):dict(title=row.title,year=row.release_date.year if row.release_date else None) for row in s.scalars(select(m.MovieSnapshot).where(m.MovieSnapshot.dataset_id==c.dataset_id,m.MovieSnapshot.movie_id.in_(ids)))} if ids else {}
    if len(movies)!=len(ids):problem('whatif_catalog_integrity','Pinned shared-film evidence is missing.',503)
    return w.Inputs(draft_id=d.id,source_input_hash=result.input_hash,source_output_hash=result.output_hash,slot=body.slot,person_id=body.person_id,manifest=MANIFEST,baseline=baseline,alternative=alternative,evidence_movies=movies)

def checked(row):
    try:
        if canonical_hash(row.inputs)!=row.input_hash or canonical_hash(row.outputs)!=row.output_hash:raise ValueError('Hash mismatch.')
        inputs=w.Inputs.model_validate(row.inputs);output=w.Comparison.model_validate(row.outputs)
        if (inputs.draft_id,inputs.slot,inputs.person_id,inputs.source_input_hash,inputs.source_output_hash)!=(row.draft_id,Slot(row.slot),row.person_id,row.source_input_hash,row.source_output_hash):raise ValueError('Input identity mismatch.')
        if (output.draft_id,output.slot,output.alternative_card.person_id,output.source_input_hash,output.source_output_hash,output.version)!=(row.draft_id,Slot(row.slot),row.person_id,row.source_input_hash,row.source_output_hash,row.version):raise ValueError('Output identity mismatch.')
        return w.Saved(analysis_id=row.id,created_at=row.created_at,input_hash=row.input_hash,output_hash=row.output_hash,comparison=output).model_dump(mode='json')
    except ValueError:problem('whatif_integrity','Saved hypothetical report failed its integrity check.',503)

def create(engine,token,draft_id,body):
    data=body.model_dump(mode='json');digest=canonical_hash(data)
    with Session(engine) as s,s.begin():
        d,c,frozen,result=access(s,token,draft_id,write=True)
        receipt=s.get(m.WhatIfReceipt,(draft_id,body.request_id))
        if receipt:
            if receipt.body_hash!=digest:problem('idempotency_conflict','Request ID was used for a different what-if comparison.',409)
            return checked(s.get(m.WhatIfAnalysis,receipt.analysis_id))
        row=s.scalar(select(m.WhatIfAnalysis).where(m.WhatIfAnalysis.draft_id==draft_id,m.WhatIfAnalysis.version==VERSION,m.WhatIfAnalysis.slot==body.slot.value,m.WhatIfAnalysis.person_id==body.person_id))
        if row is None:
            inputs=build_inputs(s,d,c,frozen,result,body);value=compare(inputs)
            payload=inputs.model_dump(mode='json');key=canonical_hash([VERSION,str(draft_id),result.input_hash,body.slot.value,str(body.person_id)])
            row=m.WhatIfAnalysis(id=uuid5(NAMESPACE_URL,'cinedraft:whatif:'+key),draft_id=draft_id,source_input_hash=result.input_hash,source_output_hash=result.output_hash,version=VERSION,slot=body.slot.value,person_id=body.person_id,input_hash=canonical_hash(payload),inputs=payload,output_hash=canonical_hash(value),outputs=value)
            s.add(row);s.flush()
        response=checked(row)
        s.add(m.WhatIfReceipt(draft_id=draft_id,request_id=body.request_id,analysis_id=row.id,body_hash=digest,request_body=data));s.flush()
        return response

def read(engine,token,draft_id,analysis_id):
    with Session(engine) as s,s.begin():
        access(s,token,draft_id);row=s.get(m.WhatIfAnalysis,analysis_id)
        if row is None or row.draft_id!=draft_id:problem('whatif_not_found','Hypothetical report not found.',404)
        return checked(row)

def history(engine,token,draft_id,limit=10,offset=0):
    with Session(engine) as s,s.begin():
        access(s,token,draft_id)
        rows=s.scalars(select(m.WhatIfAnalysis).where(m.WhatIfAnalysis.draft_id==draft_id).order_by(m.WhatIfAnalysis.created_at.desc(),m.WhatIfAnalysis.id).offset(offset).limit(limit+1)).all();items=[]
        for row in rows[:limit]:
            value=checked(row)['comparison'];items.append(dict(analysis_id=row.id,slot=row.slot,person_id=row.person_id,name=value['alternative_card']['name'],created_at=row.created_at,unchanged=value['unchanged']))
        return dict(items=items,next_offset=offset+limit if len(rows)>limit else None)
