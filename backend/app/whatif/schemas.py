"""Separate hypothetical teams: no historical offer, pick, revision or official result is forged."""
from datetime import datetime
from typing import Annotated,Literal
from uuid import UUID
from pydantic import Field,model_validator
from app import contracts as c
from app.drafting.schemas import LiveCard,DraftVersions,FrozenRoleProfile

class CompareRequest(c.Contract):
    request_id:UUID
    slot:c.Slot
    person_id:UUID

class Selection(c.Contract):
    slot:c.Slot
    person_id:UUID
    locked_fee_usd:c.Money

class TeamDraft(c.Contract):
    genre_id:c.GenreId
    versions:DraftVersions
    budget:c.Budget
    picks:Annotated[list[Selection],Field(min_length=8,max_length=8)]

class Team(c.Contract):
    schema_version:Literal['phase11-team-v1']='phase11-team-v1'
    synthetic:bool
    draft:TeamDraft
    cards:Annotated[list[LiveCard],Field(min_length=8,max_length=8)]
    role_features:Annotated[list[FrozenRoleProfile],Field(min_length=8,max_length=8)]
    graph_configuration:dict
    collaborations:Annotated[list[dict],Field(min_length=12,max_length=12)]
    @model_validator(mode='after')
    def complete(self):
        picks=self.draft.picks;cards={x.person_id:x for x in self.cards}
        if {x.slot for x in picks}!=set(c.Slot) or len({x.person_id for x in picks})!=8 or len(cards)!=8:raise ValueError('A hypothetical team requires eight distinct identities and all slots.')
        if sum(p.locked_fee_usd for p in picks)!=self.draft.budget.talent_spend_usd:raise ValueError('Hypothetical fees must reconcile.')
        expected={(p.person_id,c.SLOT_ROLES[p.slot]) for p in picks}
        if {(p.person_id,p.role) for p in self.role_features}!=expected:raise ValueError('Role profiles must match the team.')
        for p in picks:
            card=cards.get(p.person_id)
            if card is None or card.role!=c.SLOT_ROLES[p.slot] or card.hiring_fee_usd!=p.locked_fee_usd or card.versions!=self.draft.versions or (card.source=='fixture')!=self.synthetic:raise ValueError('Hypothetical card, fee, role or version mismatch.')
        return self

class Inputs(c.Contract):
    schema_version:Literal['phase11-inputs-v1']='phase11-inputs-v1'
    draft_id:UUID
    source_input_hash:c.Hash
    source_output_hash:c.Hash
    slot:c.Slot
    person_id:UUID
    manifest:dict
    baseline:Team
    alternative:Team
    evidence_movies:dict

class Distribution(c.Contract):
    p10:str
    median:str
    p90:str
class Metric(c.Contract):
    key:str
    label:str
    unit:str
    baseline:Distribution
    alternative:Distribution
    paired_delta:Distribution
    positive_samples:int
    equal_samples:int
    negative_samples:int
class Comparison(c.Contract):
    schema_version:Literal['phase11-result-v1']='phase11-result-v1'
    hypothetical:Literal[True]=True
    version:str
    draft_id:UUID
    source_input_hash:c.Hash
    source_output_hash:c.Hash
    sample_count:int
    sample_hash:c.Hash
    unchanged:bool
    synthetic:bool
    slot:c.Slot
    baseline_card:LiveCard
    alternative_card:LiveCard
    budget:dict
    metrics:list[Metric]
    score:dict
    explanation:dict
    reproducibility:dict
class Saved(c.Contract):
    analysis_id:UUID
    created_at:datetime
    input_hash:c.Hash
    output_hash:c.Hash
    comparison:Comparison
class Candidate(c.Contract):
    card:LiveCard
    is_original:bool
    selectable:bool
    blocked_reason:str|None
    hypothetical_spend_usd:int
class Candidates(c.Contract):
    slot:c.Slot
    original:LiveCard
    available_after_refund_usd:int
    items:list[Candidate]
    next_offset:int|None
class HistoryItem(c.Contract):
    analysis_id:UUID
    slot:c.Slot
    person_id:UUID
    name:str
    created_at:datetime
    unchanged:bool
class History(c.Contract):
    items:list[HistoryItem]
    next_offset:int|None
