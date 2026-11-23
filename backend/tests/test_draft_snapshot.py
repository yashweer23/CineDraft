from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.domain import Slot,SLOT_ROLES
from app.drafting.schemas import DraftVersions,FrozenDraft
from app.drafting.rules import RULES,SCORING


def test_phase7_snapshot_freezes_role_inputs_and_rejects_wrong_role_identity():
    versions={key:('a'*64 if 'hash' in key else 'fixture:v1') for key in DraftVersions.model_fields}
    picks=[];cards=[];profiles=[]
    for slot in Slot:
        pid=str(uuid4());role=SLOT_ROLES[slot].value
        picks.append(dict(slot=slot.value,person_id=pid,locked_fee_usd=100000,offer_id=str(uuid4())))
        cards.append(dict(person_id=pid,name='Synthetic person',role=role,hiring_fee_usd=100000,source='fixture',talent_strength=50,genre_fit=50,specialties=[],coverage='Synthetic',notable_works=[],versions=versions))
        profiles.append(dict(person_id=pid,role=role,attributes={'popularity_percentile':None},evidence={'synthetic':True}))
    data=dict(schema_version='phase7-v1',synthetic=True,seed='synthetic-seed',rules_configuration=RULES,scoring_configuration=SCORING,graph_configuration={'synthetic':True},collaborations=[{} for _ in range(12)],cards=cards,role_features=profiles,
        draft=dict(draft_id=str(uuid4()),status='production_finalized',genre_id='drama',revision=9,
        budget=dict(tier='indie',total_budget_usd=10000000,reserve_usd=3500000,talent_budget_usd=6500000,talent_spend_usd=800000,talent_remaining_usd=5700000),
        picks=picks,current_offer=None,rerolls_used=0,recasts_used=0,versions=versions,synthetic=True,minimum_remaining_cost_usd=0,can_reroll=False,reroll_unavailable_reason='Completed',snapshot_hash=None))
    frozen=FrozenDraft.model_validate(data)
    assert FrozenDraft.model_validate_json(frozen.model_dump_json())==frozen
    assert frozen.role_features[0].attributes['popularity_percentile'] is None
    for field,value in [('person_id',str(uuid4())),('role','composer')]:
        changed=deepcopy(data);changed['role_features'][0][field]=value
        with pytest.raises(ValidationError):FrozenDraft.model_validate(changed)


def test_exported_phase7_snapshot_schema_matches_code():
    path=Path(__file__).resolve().parents[2]/'contracts/snapshot.phase7.schema.json'
    assert json.loads(path.read_text())==FrozenDraft.model_json_schema()
