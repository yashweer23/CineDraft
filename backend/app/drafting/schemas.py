from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, model_validator
from app import contracts as c

class DraftVersions(c.VersionBundle):
    catalog_id:c.VersionId
    catalog_hash:c.Hash
    graph_id:c.VersionId
    graph_hash:c.Hash
    feature_hash:c.Hash
    pricing_hash:c.Hash

class LiveWork(c.NotableWork):
    poster_url:str|None

class LiveCard(c.CandidateCard):
    versions:DraftVersions
    notable_works:Annotated[list[LiveWork],Field(max_length=5)]

class LiveCandidate(c.OfferedCandidate):
    card:LiveCard

class LiveOffer(c.OfferView):
    candidates:Annotated[list[LiveCandidate],Field(max_length=3)]
    generated_at_revision:c.Revision

class LiveDraft(c.DraftView):
    versions:DraftVersions
    current_offer:LiveOffer|None
    synthetic:bool
    minimum_remaining_cost_usd:c.Money|None
    can_reroll:bool
    reroll_unavailable_reason:str|None
    snapshot_hash:c.Hash|None

class FrozenRoleProfile(c.Contract):
    person_id:UUID
    role:c.Role
    attributes:dict
    evidence:dict

class FrozenDraft(c.FrozenInputs):
    schema_version:Literal['phase7-v1']='phase7-v1'
    draft:LiveDraft
    cards:Annotated[list[LiveCard],Field(min_length=8,max_length=8)]
    role_features:Annotated[list[FrozenRoleProfile],Field(min_length=8,max_length=8)]
    graph_configuration:dict
    collaborations:Annotated[list[dict],Field(min_length=12,max_length=12)]

    @model_validator(mode='after')
    def profiles_match_roster(self):
        expected={(p.person_id,c.SLOT_ROLES[p.slot]) for p in self.draft.picks}
        if {(p.person_id,p.role) for p in self.role_features}!=expected:
            raise ValueError('Frozen role profiles must match all eight selected identities and roles')
        return self

class SessionCreated(c.Contract):
    access_token:str
    token_type:Literal['bearer']='bearer'
    expires_at:datetime

class SessionRevoked(c.Contract):
    revoked:Literal[True]=True

class DraftPage(c.Contract):
    items:list[LiveDraft]
    next_offset:int|None

class RosterMember(c.Contract):
    slot:c.Slot
    locked_fee_usd:c.Money
    card:LiveCard

class RosterView(c.Contract):
    draft_id:UUID
    revision:c.Revision
    members:Annotated[list[RosterMember],Field(max_length=8)]

class TierAvailability(c.Contract):
    tier:c.Tier
    total_budget_usd:c.Money
    talent_budget_usd:c.Money
    enabled:bool
    minimum_cost_usd:c.Money|None
    reason:str|None

class CatalogAvailability(c.Contract):
    catalog_id:c.VersionId
    dataset_id:c.VersionId
    pricing_id:c.VersionId
    graph_id:c.VersionId
    synthetic:bool
    tiers:list[TierAvailability]
    rules:dict
    simulation_available:Literal[True]=True
