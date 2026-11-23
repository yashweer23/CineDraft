from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.domain import Role
from app.contracts import GenreId, Money

Score = Annotated[float, Field(ge=0, le=100)]
class Output(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class TalentVersion(Output):
    dataset_id: str
    feature_id: str
    pricing_id: str
    feature_version: str
    pricing_version: str
    ranking_version: str
    feature_hash: str
    pricing_hash: str
    created_at: datetime
    source: str
    playable: Literal[False] = False

class TalentVersions(Output):
    items: list[TalentVersion]
    next_offset: int | None

class RankedWork(Output):
    movie_id: UUID
    source: Literal["tmdb", "fixture"]
    source_key: str
    title: str
    year: int | None
    poster_url: str | None
    audience_rating: Annotated[float, Field(ge=0, le=10)] | None
    vote_count: int | None
    credited_jobs: list[str]
    rank: Annotated[int, Field(ge=1, le=5)]
    notability: Annotated[float, Field(ge=0, le=1)]
    reception_available: bool
    components: dict[str, float]

class TalentProfile(Output):
    person_id: UUID
    name: str
    source: Literal["tmdb", "fixture"]
    source_key: str
    role: Role
    profile_url: str | None
    dataset_id: str
    feature_id: str
    pricing_id: str
    ranking_version: str
    currency: Literal["USD"] = "USD"
    fee_is_fictional: Literal[True] = True
    hiring_fee_usd: Money
    talent_strength: Score
    reception: Score
    experience: Score
    versatility: Score
    popularity_percentile: Score | None
    selected_genre: GenreId
    genre_fit: Score
    genre_evidence_movies: int
    genre_catalog_gap: bool
    specialties: list[GenreId]
    career_span_years: int | None
    coverage: dict
    notable_works: Annotated[list[RankedWork], Field(max_length=5)]
    notable_works_label: Literal["Notable films · from our catalog"] = "Notable films · from our catalog"
    playable: Literal[False] = False

class TalentPage(Output):
    items: list[TalentProfile]
    next_offset: int | None

class TalentDetail(TalentProfile):
    evidence: dict
    pricing_explanation: dict
    feature_parameters: dict
    pricing_parameters: dict

class TalentReport(Output):
    versions: TalentVersion
    features: dict
    pricing: dict
