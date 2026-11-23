"""Single-transaction, owner-authorized classic draft commands."""
from collections import defaultdict
from copy import deepcopy
import secrets
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.domain import Slot,SLOT_ROLES,TIERS
from app.repository import canonical_hash,save_snapshot
from app.talent import api as talent_api
from app.collaboration.calculation import canonical_pair,edge_key,NO_SHARED
from app.drafting import schemas as wire
from app.drafting.assignment import minimum_assignment,legal_candidates
from app.drafting.catalog import checked_catalog,pool_for
from app.drafting.auth import authorize
from app.accounts.service import ownership_scope
from app.drafting.errors import DraftProblem
from app.drafting.rules import RULES,SCORING,PRNG_VERSION,SIMULATION_VERSION,RELATIONSHIPS,choose_offer


def fail(message,code='invalid_action',revision=None,status=409):
    raise DraftProblem(status,code,message,revision)


def versions(s,c):
    ds=s.get(m.DatasetVersion,c.dataset_id);f=s.get(m.FeatureVersion,c.feature_id)
    return wire.DraftVersions(dataset_id=c.dataset_id,feature_id=c.feature_id,pricing_id=c.pricing_id,graph_id=c.graph_id,
        catalog_id=c.id,catalog_hash=c.content_hash,graph_hash=c.configuration['graph_hash'],feature_hash=c.configuration['feature_hash'],
        pricing_hash=c.configuration['pricing_hash'],rules_id=c.rules_id,scoring_id=c.scoring_id,
        ranking_version=f.ranking_version,role_mapping_version=ds.role_mapping_version,prng_version=PRNG_VERSION,simulation_version=SIMULATION_VERSION)


def picks_for(s,d):
    positions={slot.value:i for i,slot in enumerate(Slot)}
    return sorted(s.scalars(select(m.Pick).where(m.Pick.draft_id==d.id)).all(),key=lambda p:positions[p.slot])


def unused_slots(picks):return [slot for slot in Slot if slot.value not in {p.slot for p in picks}]


def offer_view(s,offer,d):
    if offer is None:return None
    rows=s.scalars(select(m.OfferCandidate).where(m.OfferCandidate.offer_id==offer.id).order_by(m.OfferCandidate.position)).all()
    message=None
    if len(rows)<3:message=f'Only {len(rows)} alternative(s) in this frozen role pool.'
    if offer.kind=='recast' and not any(r.selectable for r in rows):message='No affordable alternative for this slot. Cancel to keep your roster.'
    return wire.LiveOffer(offer_id=offer.id,slot=offer.slot,kind=offer.kind,revision=d.revision,
        generated_at_revision=offer.revision,shortage_message=message,
        candidates=[wire.LiveCandidate(card=wire.LiveCard.model_validate(r.card_snapshot),selectable=r.selectable,blocked_reason=r.blocked_reason) for r in rows])


def view(s,d,rt,c,pool=None):
    picks=picks_for(s,d);slots=unused_slots(picks);used={str(p.person_id) for p in picks}
    offer=s.get(m.Offer,rt.current_offer_id) if rt.current_offer_id else None
    can=False;reason='Offer rerolls are only available while drafting.'
    if d.status=='awaiting_pick':
        if pool is None:pool=pool_for(s,c.pricing_id)
        if d.rerolls_used>=2:reason='Both offer rerolls have been used.'
        else:
            current={str(x) for x in s.scalars(select(m.OfferCandidate.person_id).where(m.OfferCandidate.offer_id==offer.id))}
            can=any(r.role==SLOT_ROLES[slots[0]].value and r.person_id not in used|current for r in pool)
            reason=None if can else 'No different valid offer set exists in this frozen pool.'
    minimum=None
    if d.status!='abandoned':
        if slots and pool is None:pool=pool_for(s,c.pricing_id)
        minimum=minimum_assignment(pool or [],slots,used)
    snap=s.get(m.DraftSnapshot,d.id)
    return wire.LiveDraft(draft_id=d.id,status=d.status,genre_id=d.genre_id,revision=d.revision,
        budget=dict(tier=d.tier,total_budget_usd=d.total_budget_usd,reserve_usd=d.reserve_usd,
            talent_budget_usd=d.talent_budget_usd,talent_spend_usd=d.talent_spend_usd,talent_remaining_usd=d.talent_budget_usd-d.talent_spend_usd),
        picks=[dict(slot=p.slot,person_id=p.person_id,locked_fee_usd=p.locked_fee_usd,offer_id=p.offer_id) for p in picks],
        current_offer=offer_view(s,offer,d),rerolls_used=d.rerolls_used,recasts_used=d.recasts_used,versions=versions(s,c),
        synthetic=c.configuration['source']=='fixture',minimum_remaining_cost_usd=minimum['cost_usd'] if minimum else None,
        can_reroll=can,reroll_unavailable_reason=reason,snapshot_hash=snap.input_hash if snap else None)


def cards(s,c,selected,genre):
    if not selected:return {}
    p=s.get(m.PricingVersion,c.pricing_id);f=s.get(m.FeatureVersion,c.feature_id);ds=s.get(m.DatasetVersion,c.dataset_id)
    ids=[UUID(row['talent'].person_id) for row in selected];role=selected[0]['talent'].role
    rows=s.execute(talent_api.profile_query(p,f).where(m.RoleFeature.person_id.in_(ids),m.RoleFeature.role==role)).all()
    films=talent_api.film_map(s,ds,rows);result={}
    for row in rows:
        value=talent_api.view(p,f,ds,row,films,genre)
        result[str(row[0].person_id)]=wire.LiveCard(person_id=value['person_id'],name=value['name'],role=role,
            hiring_fee_usd=value['hiring_fee_usd'],source=value['source'],talent_strength=value['talent_strength'],genre_fit=value['genre_fit'],
            specialties=value['specialties'],coverage=f"{value['coverage']['level']}: {value['coverage']['eligible_movies']} eligible films",
            notable_works=[dict(movie_id=w['movie_id'],title=w['title'],year=w['year'],credited_jobs=w['credited_jobs'],
                poster_path=films[str(w['movie_id'])][0].poster_path,poster_url=w['poster_url'],audience_rating=w['audience_rating'],vote_count=w['vote_count'],source=w['source']) for w in value['notable_works']],
            versions=versions(s,c))
    if len(result)!=len(selected):fail('Frozen candidate data is incomplete.','catalog_inconsistent',status=503)
    return result


def make_offer(s,d,c,pool,slot,kind,*,previous=None):
    picks=picks_for(s,d)
    if kind=='pick':
        used={str(p.person_id) for p in picks};remaining=[x for x in unused_slots(picks) if x!=slot];available=d.talent_budget_usd-d.talent_spend_usd
    else:
        old=next(p for p in picks if p.slot==slot.value)
        # Exclude the original person as well as the seven retained picks.
        used={str(p.person_id) for p in picks};remaining=[];available=d.talent_budget_usd-d.talent_spend_usd+old.locked_fee_usd
    rows=legal_candidates(pool,slot,remaining,used,available)
    if kind=='pick' and not any(r['selectable'] for r in rows):fail('No feasible continuation in the frozen catalog. State was preserved.','no_continuation',status=503)
    stream=f'recast:{slot.value}' if kind=='recast' else f'pick:{slot.value}:{d.revision}'
    selected=choose_offer(rows,d.seed,stream,previous)
    if previous is not None and {r['talent'].person_id for r in selected}==previous:fail('No different valid offer set exists. No reroll was consumed.','reroll_unavailable',d.revision-1)
    card_map=cards(s,c,selected,d.genre_id)
    offer=m.Offer(draft_id=d.id,slot=slot.value,kind=kind,revision=d.revision,rng_position=d.revision)
    s.add(offer);s.flush()
    for i,row in enumerate(selected,1):
        talent=row['talent'];card=card_map[talent.person_id]
        s.add(m.OfferCandidate(offer_id=offer.id,person_id=UUID(talent.person_id),position=i,fee_usd=talent.fee_usd,
            selectable=row['selectable'],blocked_reason=row['blocked_reason'],card_snapshot=card.model_dump(mode='json')))
    s.flush();offer.sealed=True;s.flush();return offer


def owned(s,owner,draft_id,*,write=False):
    query=select(m.Draft,m.DraftRuntime).join(m.DraftRuntime,m.DraftRuntime.draft_id==m.Draft.id).where(
        m.Draft.id==draft_id,ownership_scope(owner))
    row=s.execute(query.with_for_update(read=not write,of=m.Draft)).one_or_none()
    if row is None:fail('Draft not found for this session.','draft_not_found',status=404)
    d,rt=row;return d,rt,checked_catalog(s,rt.catalog_id)


def roster(engine,token,draft_id):
    """Read names and works from the exact saved offers, including after recovery.

    Separate from LiveDraft so historical phase7-v1 snapshot JSON is unchanged.
    The draft lock keeps the picks and response revision consistent with each other.
    """
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=owned(s,owner,draft_id)
        members=[]
        for pick in picks_for(s,d):
            candidate=s.scalar(select(m.OfferCandidate).where(
                m.OfferCandidate.offer_id==pick.offer_id,m.OfferCandidate.person_id==pick.person_id))
            if candidate is None:
                fail('Saved roster evidence is unavailable. Draft history was preserved.','roster_inconsistent',status=503)
            card=wire.LiveCard.model_validate(candidate.card_snapshot)
            if card.person_id!=pick.person_id or card.hiring_fee_usd!=pick.locked_fee_usd or card.role!=SLOT_ROLES[Slot(pick.slot)]:
                fail('Saved roster evidence does not match its locked pick.','roster_inconsistent',status=503)
            members.append(wire.RosterMember(slot=pick.slot,locked_fee_usd=pick.locked_fee_usd,card=card))
        return wire.RosterView(draft_id=d.id,revision=d.revision,members=members).model_dump(mode='json')


def create(engine,token,body):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token,exclusive=True)
        return create_in_session(s,owner,body)


def create_in_session(s,owner,body,*,catalog_id=None,seed=None):
    data=body.model_dump(mode='json');digest=canonical_hash(data)
    prior=s.scalar(select(m.DraftRuntime).where(m.DraftRuntime.session_id==owner.id,m.DraftRuntime.creation_request_id==body.request_id))
    if prior:
        if prior.creation_body_hash!=digest:fail('Creation request ID was used with a different body.','idempotency_conflict')
        return prior.creation_response
    c=checked_catalog(s,catalog_id);pool=pool_for(s,c.pricing_id)
    total=TIERS[body.tier];reserve=total*35//100;budget=total-reserve
    witness=minimum_assignment(pool,list(Slot))
    if witness is None or witness['cost_usd']>budget:fail('This catalog cannot complete eight unique slots within the selected talent budget.','tier_unavailable',status=422)
    d=m.Draft(owner_key_hash=owner.token_hash,status='awaiting_pick',genre_id=body.genre_id,tier=body.tier,
        total_budget_usd=total,reserve_usd=reserve,talent_budget_usd=budget,talent_spend_usd=0,revision=0,
        seed=seed if seed is not None else secrets.token_hex(32),prng_version=PRNG_VERSION,dataset_id=c.dataset_id,graph_id=c.graph_id,
        feature_id=c.feature_id,pricing_id=c.pricing_id,rules_id=c.rules_id,scoring_id=c.scoring_id,simulation_version=SIMULATION_VERSION)
    s.add(d);s.flush();offer=make_offer(s,d,c,pool,Slot.DIRECTOR,'pick')
    rt=m.DraftRuntime(draft_id=d.id,session_id=owner.id,catalog_id=c.id,creation_request_id=body.request_id,
        creation_body_hash=digest,current_offer_id=offer.id,recast_cache={})
    result=view(s,d,rt,c,pool).model_dump(mode='json');rt.creation_response=result;s.add(rt);s.flush()
    return result



def read(engine,token,draft_id):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=owned(s,owner,draft_id)
        return view(s,d,rt,c).model_dump(mode='json')


def list_drafts(engine,token,limit=5,offset=0):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token)
        ids=s.scalars(select(m.Draft.id).join(m.DraftRuntime,m.DraftRuntime.draft_id==m.Draft.id)
            .where(ownership_scope(owner))
            .order_by(m.Draft.created_at.desc(),m.Draft.id).offset(offset).limit(limit+1)).all()
        items=[]
        for draft_id in ids[:limit]:
            d,rt,c=owned(s,owner,draft_id);items.append(view(s,d,rt,c).model_dump(mode='json'))
        return {'items':items,'next_offset':offset+limit if len(ids)>limit else None}


def selected_offer(s,d,rt,body,kind):
    if rt.current_offer_id!=body.offer_id:fail('Offer is no longer current. Refresh this draft.','stale_offer',d.revision)
    offer=s.get(m.Offer,body.offer_id)
    if offer is None or not offer.sealed or offer.draft_id!=d.id or offer.kind!=kind:fail('Offer does not belong to this action.','invalid_offer',d.revision)
    return offer


def picked_candidate(s,d,offer,body,pool,*,recast=False):
    row=s.get(m.OfferCandidate,(offer.id,body.person_id))
    if row is None or not row.selectable:fail('Choose a selectable person from the current offer.','invalid_candidate',d.revision,status=422)
    picks=picks_for(s,d);used={str(p.person_id) for p in picks};slot=Slot(offer.slot)
    if recast:
        old=next(p for p in picks if p.slot==offer.slot)
        available=d.talent_budget_usd-d.talent_spend_usd+old.locked_fee_usd;remaining=[]
    else:available=d.talent_budget_usd-d.talent_spend_usd;remaining=[x for x in unused_slots(picks) if x!=slot]
    legal=next((r for r in legal_candidates(pool,slot,remaining,used,available) if r['talent'].person_id==str(body.person_id)),None)
    if legal is None or not legal['selectable'] or legal['talent'].fee_usd!=row.fee_usd:fail('Selection no longer satisfies the frozen budget and identity rules.','infeasible_pick',d.revision,status=422)
    return row


def frozen_collaborations(s,d,picks):
    roster={p.slot:p for p in picks};keys={};result=[]
    for a,b in RELATIONSHIPS:
        left,right=canonical_pair(roster[a].person_id,SLOT_ROLES[Slot(a)],roster[b].person_id,SLOT_ROLES[Slot(b)])
        keys[(a,b)]=edge_key(left,right)
    edges={e.edge_id:e for e in s.scalars(select(m.GraphEdge).where(m.GraphEdge.graph_id==d.graph_id,m.GraphEdge.edge_id.in_(list(keys.values()))))}
    evidence=defaultdict(list)
    for e in s.scalars(select(m.GraphEvidence).where(m.GraphEvidence.graph_id==d.graph_id,m.GraphEvidence.edge_id.in_(list(edges))).order_by(m.GraphEvidence.movie_id)):
        evidence[e.edge_id].append(dict(movie_id=str(e.movie_id),jobs_a=e.jobs_a,jobs_b=e.jobs_b))
    for a,b in RELATIONSHIPS:
        key=keys[(a,b)];edge=edges.get(key)
        left,right=canonical_pair(roster[a].person_id,SLOT_ROLES[Slot(a)],roster[b].person_id,SLOT_ROLES[Slot(b)])
        result.append(dict(slot_a=a,slot_b=b,canonical_a=list(left),canonical_b=list(right),edge_id=key if edge else None,
            shared_movie_count=edge.shared_movie_count if edge else 0,bonus=edge.bonus if edge else 0,
            message='Shared credits found in this dataset.' if edge else NO_SHARED,evidence=evidence[key]))
    return result


def finalize_snapshot(s,d,rt,c,pool):
    picks=picks_for(s,d)
    if len(picks)!=8 or len({p.person_id for p in picks})!=8:fail('Finalization requires all eight distinct people.','incomplete_roster',d.revision)
    prices={(r.person_id,r.role):r.fee_usd for r in pool}
    if any(prices.get((str(p.person_id),SLOT_ROLES[Slot(p.slot)].value))!=p.locked_fee_usd for p in picks):fail('Roster does not match its pinned price version.','catalog_inconsistent',status=503)
    stored_cards=[wire.LiveCard.model_validate(s.get(m.OfferCandidate,(p.offer_id,p.person_id)).card_snapshot) for p in picks]
    profiles=[s.get(m.RoleFeature,(c.feature_id,p.person_id,SLOT_ROLES[Slot(p.slot)].value)) for p in picks]
    value=wire.FrozenDraft(role_features=[dict(person_id=f.person_id,role=f.role,attributes=f.attributes,evidence=f.evidence) for f in profiles],synthetic=c.configuration['source']=='fixture',draft=view(s,d,rt,c,pool),seed=d.seed,cards=stored_cards,
        rules_configuration=s.get(m.RulesVersion,c.rules_id).configuration,scoring_configuration=s.get(m.ScoringVersion,c.scoring_id).configuration,
        graph_configuration=s.get(m.GraphVersion,c.graph_id).configuration,collaborations=frozen_collaborations(s,d,picks))
    save_snapshot(s,value)


def mutate(engine,token,draft_id,command,body):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=owned(s,owner,draft_id,write=True)
        if s.scalar(select(m.DraftRoom.id).where(m.DraftRoom.draft_id==d.id)) is not None:
            fail('Use the multiplayer room for this shared film.', 'room_managed')
        return mutate_in_session(s,d,rt,c,command,body)


def mutate_in_session(s,d,rt,c,command,body):
    """Caller must hold the draft write lock; shared rooms also hold their room lock."""
    data=body.model_dump(mode='json');digest=canonical_hash(data)
    prior=s.scalar(select(m.ActionRecord).where(m.ActionRecord.draft_id==d.id,m.ActionRecord.command==command,m.ActionRecord.request_id==body.request_id))
    if prior:
        if prior.body_hash!=digest:fail('Request ID was used with a different body.','idempotency_conflict',d.revision)
        return prior.response_body
    if body.expected_revision!=d.revision:fail('Draft changed. Refresh before trying a new action.','stale_revision',d.revision)
    from app.challenges.service import guard_action
    guard_action(s,d.id,command)
    before=d.revision;pool=pool_for(s,c.pricing_id)
    if command=='pick':
        if d.status!='awaiting_pick':fail('Draft is not waiting for a pick.',revision=d.revision)
        offer=selected_offer(s,d,rt,body,'pick');candidate=picked_candidate(s,d,offer,body,pool)
        d.revision+=1;s.add(m.Pick(draft_id=d.id,slot=offer.slot,person_id=body.person_id,offer_id=offer.id,locked_fee_usd=candidate.fee_usd,picked_at_revision=d.revision))
        d.talent_spend_usd+=candidate.fee_usd;s.flush();remaining=unused_slots(picks_for(s,d))
        if remaining:rt.current_offer_id=make_offer(s,d,c,pool,remaining[0],'pick').id
        else:d.status='recast_available';rt.current_offer_id=None
    elif command=='reroll':
        if d.status!='awaiting_pick' or d.rerolls_used>=2:fail('No offer reroll is available.',revision=d.revision)
        offer=selected_offer(s,d,rt,body,'pick')
        previous={str(x) for x in s.scalars(select(m.OfferCandidate.person_id).where(m.OfferCandidate.offer_id==offer.id))}
        d.revision+=1;replacement=make_offer(s,d,c,pool,Slot(offer.slot),'pick',previous=previous)
        rt.current_offer_id=replacement.id;d.rerolls_used+=1
    elif command=='preview_recast':
        if d.status!='recast_available' or d.recasts_used:fail('Recast preview is not available.',revision=d.revision)
        d.revision+=1;key=body.slot.value;cached=rt.recast_cache.get(key)
        if cached:offer=s.get(m.Offer,UUID(cached))
        else:
            offer=make_offer(s,d,c,pool,body.slot,'recast');rt.recast_cache={**rt.recast_cache,key:str(offer.id)}
        rt.current_offer_id=offer.id;d.status='recast_preview'
    elif command=='cancel_recast':
        if d.status!='recast_preview':fail('There is no open recast preview.',revision=d.revision)
        selected_offer(s,d,rt,body,'recast');d.revision+=1;d.status='recast_available';rt.current_offer_id=None
    elif command=='confirm_recast':
        if d.status!='recast_preview' or d.recasts_used:fail('Recast confirmation is not available.',revision=d.revision)
        offer=selected_offer(s,d,rt,body,'recast');candidate=picked_candidate(s,d,offer,body,pool,recast=True)
        pick=next(p for p in picks_for(s,d) if p.slot==offer.slot);d.revision+=1
        d.talent_spend_usd+=candidate.fee_usd-pick.locked_fee_usd
        pick.person_id=body.person_id;pick.offer_id=offer.id;pick.locked_fee_usd=candidate.fee_usd;pick.picked_at_revision=d.revision
        d.recasts_used=1;d.status='review_locked';rt.current_offer_id=None;rt.recast_cache={}
    elif command=='finalize':
        if d.status not in ('recast_available','review_locked') or rt.current_offer_id:fail('Complete the roster and close recast preview before finalizing.',revision=d.revision)
        d.revision+=1;d.status='production_finalized';s.flush();finalize_snapshot(s,d,rt,c,pool)
    elif command=='abandon':
        if d.status not in ('awaiting_pick','recast_available','recast_preview','review_locked'):fail('Only an unfinished draft can be abandoned.',revision=d.revision)
        d.revision+=1;d.status='abandoned';rt.current_offer_id=None;rt.recast_cache={}
    else:fail('Unsupported draft command.',status=422)
    s.flush();result=view(s,d,rt,c,pool).model_dump(mode='json')
    s.add(m.ActionRecord(draft_id=d.id,command=command,request_id=body.request_id,body_hash=digest,request_body=data,
        response_body=result,response_status=200,revision_before=before,revision_after=d.revision));s.flush()
    return result
