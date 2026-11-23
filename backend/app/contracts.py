"""Typed proposed wire contracts. Game endpoints are NOT mounted in Phase 3."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.domain import DraftStatus, Role, Slot, SLOT_ROLES, TIERS

Money = Annotated[int, Field(strict=True, ge=0, le=9_007_199_254_740_991)]
Revision = Annotated[int, Field(strict=True, ge=0)]
VersionId = Annotated[str, Field(min_length=1, max_length=100)]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Tier = Literal["indie", "studio", "blockbuster"]
GenreId = Literal["action", "adventure", "comedy", "crime", "drama", "horror", "mystery", "romance", "science_fiction", "thriller"]

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class VersionBundle(Contract):
    dataset_id: VersionId
    feature_id: VersionId
    pricing_id: VersionId
    rules_id: VersionId
    scoring_id: VersionId
    ranking_version: VersionId
    role_mapping_version: VersionId
    prng_version: VersionId
    simulation_version: VersionId

class Budget(Contract):
    tier: Tier
    currency: Literal["USD"] = "USD"
    total_budget_usd: Money
    reserve_usd: Money
    talent_budget_usd: Money
    talent_spend_usd: Money
    talent_remaining_usd: Money

    @model_validator(mode="after")
    def accounting(self):
        if self.total_budget_usd != TIERS[self.tier]:
            raise ValueError("Budget must match the selected tier")
        if self.reserve_usd != self.total_budget_usd * 35 // 100:
            raise ValueError("Production reserve must be 35 percent")
        if self.talent_budget_usd != self.total_budget_usd - self.reserve_usd:
            raise ValueError("Talent allocation must reconcile")
        if self.talent_spend_usd + self.talent_remaining_usd != self.talent_budget_usd:
            raise ValueError("Talent spending must reconcile")
        return self

class NotableWork(Contract):
    movie_id: UUID
    title: Annotated[str, Field(min_length=1)]
    year: Annotated[int, Field(strict=True, ge=1800, le=9999)] | None
    credited_jobs: Annotated[list[str], Field(min_length=1)]
    poster_path: str | None
    audience_rating: Annotated[float, Field(ge=0, le=10)] | None
    vote_count: Annotated[int, Field(strict=True, ge=0)] | None
    source: Literal["tmdb", "fixture"]

class CandidateCard(Contract):
    person_id: UUID
    name: str
    role: Role
    hiring_fee_usd: Money
    fee_is_fictional: Literal[True] = True
    source: Literal["tmdb", "fixture"]
    talent_strength: Annotated[float, Field(ge=0, le=100)] | None
    genre_fit: Annotated[float, Field(ge=0, le=100)] | None
    specialties: list[GenreId]
    coverage: str
    notable_works: Annotated[list[NotableWork], Field(max_length=5)]
    versions: VersionBundle

    @model_validator(mode="after")
    def unique_films(self):
        if len({w.movie_id for w in self.notable_works}) != len(self.notable_works):
            raise ValueError("A film appears at most once per role card")
        return self

class OfferedCandidate(Contract):
    card: CandidateCard
    selectable: bool
    blocked_reason: str | None

    @model_validator(mode="after")
    def reason(self):
        if self.selectable != (self.blocked_reason is None):
            raise ValueError("Only blocked candidates have a blocked reason")
        return self

class OfferView(Contract):
    offer_id: UUID
    slot: Slot
    kind: Literal["pick", "recast"]
    revision: Revision
    candidates: Annotated[list[OfferedCandidate], Field(max_length=3)]
    shortage_message: str | None

    @model_validator(mode="after")
    def candidates_match(self):
        ids = [c.card.person_id for c in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate person in offer")
        if any(c.card.role != SLOT_ROLES[self.slot] for c in self.candidates):
            raise ValueError("Candidate role does not match the slot")
        if self.kind == "pick" and not any(c.selectable for c in self.candidates):
            raise ValueError("A pick offer must contain a legal choice")
        if len(ids) < 3 and not self.shortage_message:
            raise ValueError("A short offer must explain its shortage")
        return self

class PickView(Contract):
    slot: Slot
    person_id: UUID
    locked_fee_usd: Money
    offer_id: UUID

class DraftView(Contract):
    draft_id: UUID
    status: DraftStatus
    genre_id: GenreId
    revision: Revision
    budget: Budget
    picks: Annotated[list[PickView], Field(max_length=8)]
    current_offer: OfferView | None
    rerolls_used: Annotated[int, Field(strict=True, ge=0, le=2)]
    recasts_used: Annotated[int, Field(strict=True, ge=0, le=1)]
    versions: VersionBundle

    @model_validator(mode="after")
    def roster(self):
        if len({p.person_id for p in self.picks}) != len(self.picks) or len({p.slot for p in self.picks}) != len(self.picks):
            raise ValueError("Roster contains duplicate people or slots")
        if sum(p.locked_fee_usd for p in self.picks) != self.budget.talent_spend_usd:
            raise ValueError("Pick fees must match talent spending")
        if self.current_offer and self.current_offer.revision != self.revision:
            raise ValueError("Current offer revision must match draft")
        return self

class CreateDraftRequest(Contract):
    request_id: UUID
    genre_id: GenreId
    tier: Tier
    mode: Literal["classic"] = "classic"

class MutationRequest(Contract):
    request_id: UUID
    expected_revision: Revision

class PickRequest(MutationRequest):
    offer_id: UUID
    person_id: UUID

class RerollRequest(MutationRequest):
    offer_id: UUID

class RecastPreviewRequest(MutationRequest):
    slot: Slot

class RecastCancelRequest(MutationRequest):
    offer_id: UUID

class RecastConfirmRequest(PickRequest):
    pass

class FrozenInputs(Contract):
    schema_version: Literal["phase3-v1"] = "phase3-v1"
    synthetic: bool
    draft: DraftView
    seed: Annotated[str, Field(min_length=1, max_length=128)]
    cards: Annotated[list[CandidateCard], Field(min_length=8, max_length=8)]
    rules_configuration: dict
    scoring_configuration: dict
    rounding: Literal["integer-usd-half-up"] = "integer-usd-half-up"

    @model_validator(mode="after")
    def complete(self):
        if len(self.draft.picks) != 8 or {p.slot for p in self.draft.picks} != set(Slot):
            raise ValueError("Finalization requires all eight distinct slots")
        if self.draft.status != DraftStatus.PRODUCTION_FINALIZED or self.draft.current_offer is not None:
            raise ValueError("Snapshot requires finalized state with no active offer")
        cards = {c.person_id: c for c in self.cards}
        if len(cards) != 8:
            raise ValueError("Final cards must describe eight distinct people")
        for pick in self.draft.picks:
            card = cards.get(pick.person_id)
            if not card or card.role != SLOT_ROLES[pick.slot] or card.hiring_fee_usd != pick.locked_fee_usd or card.versions != self.draft.versions:
                raise ValueError("Frozen card does not match its pick and versions")
            if (card.source == "fixture") != self.synthetic:
                raise ValueError("Synthetic marker must match card sources")
        return self

class ResultView(Contract):
    draft_id: UUID
    input_hash: Hash
    simulation_id: UUID
    simulation_version: VersionId
    synthetic: bool
    critics: Annotated[float, Field(ge=0, le=100)]
    audience: Annotated[float, Field(ge=0, le=100)]
    studio_score: Annotated[int, Field(strict=True, ge=0, le=100)]
    production_cost_usd: Money
    marketing_usd: Money
    worldwide_gross_usd: Money
    studio_receipts_usd: Money
    profit_usd: Annotated[int, Field(strict=True)]
    weekly_gross_usd: Annotated[list[Money], Field(min_length=4, max_length=4)]
    explanation: dict

    @model_validator(mode="after")
    def reconcile(self):
        if self.profit_usd != self.studio_receipts_usd - self.production_cost_usd - self.marketing_usd:
            raise ValueError("Profit does not reconcile")
        if sum(self.weekly_gross_usd) != self.worldwide_gross_usd:
            raise ValueError("Weekly totals do not reconcile")
        return self

class CatalogPage(Contract):
    items: list[CandidateCard]
    next_cursor: str | None
    dataset_id: VersionId

class GenreView(Contract):
    id: GenreId
    name: str

class ContractErrorDetail(Contract):
    code: str
    message: str
    current_revision: Revision | None = None

class ContractError(Contract):
    error: ContractErrorDetail
    request_id: UUID
