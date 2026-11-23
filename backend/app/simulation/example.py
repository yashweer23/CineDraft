"""Explicit synthetic inputs for arithmetic exercises. Never imported or published."""
from uuid import NAMESPACE_URL,uuid5
from app.domain import Slot,SLOT_ROLES,TIERS,GENRES
from app.repository import canonical_hash
from app.drafting.schemas import FrozenDraft
from app.drafting.rules import RULES,SCORING,RULES_ID,SCORING_ID,SIMULATION_VERSION,PRNG_VERSION,RELATIONSHIPS
from app.talent.calculation import FEATURE_VERSION
from app.collaboration.calculation import canonical_pair,edge_key,NO_SHARED


def identity(key):return uuid5(NAMESPACE_URL,'cinedraft:phase8:synthetic:'+key)


def synthetic_snapshot(*,seed='phase8-arithmetic-example',talent=80,genre_fit=60,popularity=50,shared_films=0,tier='indie',spend=3250000):
    graph={'synthetic':True,'purpose':'Phase 8 database-free arithmetic example'}
    versions=dict(dataset_id='fixture:phase8-example',feature_id='features:phase8-example',pricing_id='pricing:phase8-example',
        graph_id='graph:phase8-example',catalog_id='draft-catalog:phase8-example',rules_id=RULES_ID,scoring_id=SCORING_ID,
        ranking_version='notability-1.0',role_mapping_version='fixture:roles',prng_version=PRNG_VERSION,simulation_version=SIMULATION_VERSION,
        graph_hash=canonical_hash(graph),catalog_hash='a'*64,feature_hash='b'*64,pricing_hash='c'*64)
    picks=[];cards=[];profiles=[];roster={}
    for i,slot in enumerate(Slot):
        pid=identity(slot.value);roster[slot.value]=pid;role=SLOT_ROLES[slot].value;fee=spend//8+(spend%8 if i==7 else 0)
        picks.append(dict(slot=slot.value,person_id=pid,offer_id=identity('offer:'+slot.value),locked_fee_usd=fee))
        cards.append(dict(person_id=pid,name='Synthetic '+slot.value.replace('_',' ').title(),role=role,hiring_fee_usd=fee,
            source='fixture',talent_strength=talent,genre_fit=genre_fit,specialties=[],coverage='Synthetic arithmetic only',notable_works=[],versions=versions))
        profiles.append(dict(person_id=pid,role=role,attributes={'schema_version':FEATURE_VERSION,'talent_strength':talent,'genre_fit':{g:genre_fit for g in GENRES},
            'popularity_percentile':popularity,'coverage':{'level':'broader','eligible_movies':10,'synthetic':True}},evidence={'synthetic':True,'genre_catalog_gaps':[]}))
    edges=[]
    for a,b in RELATIONSHIPS:
        left,right=canonical_pair(roster[a],SLOT_ROLES[Slot(a)],roster[b],SLOT_ROLES[Slot(b)])
        edges.append(dict(slot_a=a,slot_b=b,canonical_a=list(left),canonical_b=list(right),edge_id=edge_key(left,right) if shared_films else None,
            shared_movie_count=shared_films,bonus=min(12,4*shared_films),message='Synthetic shared evidence.' if shared_films else NO_SHARED,
            evidence=[dict(movie_id=str(identity('film:'+str(i))),jobs_a=['Synthetic credited job'],jobs_b=['Synthetic credited job']) for i in range(shared_films)]))
    total=TIERS[tier];reserve=total*35//100;envelope=total-reserve
    return FrozenDraft(synthetic=True,seed=seed,cards=cards,role_features=profiles,rules_configuration=RULES,scoring_configuration=SCORING,
        graph_configuration=graph,collaborations=edges,draft=dict(draft_id=identity('draft'),status='production_finalized',genre_id='drama',revision=9,
        budget=dict(tier=tier,total_budget_usd=total,reserve_usd=reserve,talent_budget_usd=envelope,talent_spend_usd=spend,talent_remaining_usd=envelope-spend),
        picks=picks,current_offer=None,rerolls_used=0,recasts_used=0,versions=versions,synthetic=True,minimum_remaining_cost_usd=0,
        can_reroll=False,reroll_unavailable_reason='Finalized',snapshot_hash=None))
