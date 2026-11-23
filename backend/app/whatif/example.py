"""Invented substitution: arithmetic exercise, never a saved production."""
from app.simulation.example import synthetic_snapshot,identity
from app.simulation.engine import simulate
from app.repository import canonical_hash
from app.collaboration.calculation import canonical_pair
from app.domain import SLOT_ROLES,Slot
from app.whatif.engine import project,MANIFEST
from app.whatif.schemas import Team,Inputs

def example_inputs(*,control=False):
    frozen=synthetic_snapshot();source=canonical_hash(frozen.model_dump(mode='json'))
    baseline=project(frozen);data=baseline.model_dump(mode='json');old=data['draft']['picks'][0]['person_id'];new=str(identity('phase11:alternative-director'))
    if not control:
        fee=450000;delta=fee-data['draft']['picks'][0]['locked_fee_usd']
        data['draft']['picks'][0].update(person_id=new,locked_fee_usd=fee)
        data['draft']['budget']['talent_spend_usd']+=delta;data['draft']['budget']['talent_remaining_usd']-=delta
        data['cards'][0].update(person_id=new,name='Synthetic Alternative Director',hiring_fee_usd=fee,talent_strength=90,genre_fit=85)
        profile=data['role_features'][0];profile['person_id']=new;profile['attributes']['talent_strength']=90;profile['attributes']['genre_fit']['drama']=85
        roster={p['slot']:p['person_id'] for p in data['draft']['picks']}
        for e in data['collaborations']:
            a,b=e['slot_a'],e['slot_b'];left,right=canonical_pair(roster[a],SLOT_ROLES[Slot(a)],roster[b],SLOT_ROLES[Slot(b)])
            e.update(canonical_a=list(left),canonical_b=list(right))
    return Inputs(draft_id=frozen.draft.draft_id,source_input_hash=source,source_output_hash=canonical_hash(simulate(frozen,source)),slot='director',person_id=old if control else new,manifest=MANIFEST,baseline=baseline,alternative=Team.model_validate(data),evidence_movies={})
