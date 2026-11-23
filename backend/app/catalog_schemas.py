from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class DatasetInfo(BaseModel):
    id: str
    source: str
    created_at: datetime
    scope_version: str
    role_mapping_version: str
    report: dict
    playable: Literal[False] = False

class DatasetPage(BaseModel):
    items: list[DatasetInfo]
    next_offset: int | None

class MovieInfo(BaseModel):
    movie_id: UUID
    source: str
    source_key: str
    title: str
    release_date: date | None
    runtime_minutes: int | None
    audience_rating: float | None
    vote_count: int | None
    poster_url: str | None
    eligibility: str
    eligibility_reason: str

class MoviePage(BaseModel):
    dataset_id: str
    items: list[MovieInfo]
    next_offset: int | None

class PersonInfo(BaseModel):
    person_id: UUID
    source: str
    source_key: str
    name: str
    profile_url: str | None
    coverage: dict

class PersonPage(BaseModel):
    dataset_id: str
    items: list[PersonInfo]
    next_offset: int | None

class WorkInfo(MovieInfo):
    credited_jobs: list[str]

class FilmographyPage(BaseModel):
    dataset_id: str
    person_id: UUID
    role: str
    ordering: Literal["release_date_desc_then_movie_id"] = "release_date_desc_then_movie_id"
    ranked_notable_works: Literal[False] = False
    items: list[WorkInfo]
    next_offset: int | None
