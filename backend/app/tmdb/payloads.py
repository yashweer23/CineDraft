"""Validated subset of upstream responses. Unknown fields are not persisted."""
import re
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
Nonnegative = Annotated[float, Field(ge=0, le=9_999_999_999, allow_inf_nan=False)]

class Payload(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False, hide_input_in_errors=True)

class NamedId(Payload):
    id: SourceId
    name: Annotated[str, Field(min_length=1, max_length=500)]

class CreditPayload(Payload):
    id: SourceId
    name: Annotated[str, Field(min_length=1, max_length=240)]
    credit_id: Annotated[str, Field(max_length=200)] | None = None
    job: Annotated[str, Field(max_length=120)] | None = None
    department: Annotated[str, Field(max_length=120)] | None = None
    character: Annotated[str, Field(max_length=500)] | None = None
    order: Annotated[int, Field(strict=True, ge=0)] | None = None
    profile_path: Annotated[str, Field(max_length=500)] | None = None
    popularity: Nonnegative | None = None

class CreditsPayload(Payload):
    cast: list[CreditPayload]
    crew: list[CreditPayload]

class KeywordsPayload(Payload):
    keywords: list[NamedId]

class MoviePayload(Payload):
    id: SourceId
    title: Annotated[str, Field(min_length=1, max_length=500)]
    original_language: Annotated[str, Field(max_length=10)] | None = None
    release_date: date | None = None
    runtime: Annotated[int, Field(strict=True, ge=0)] | None = None
    status: str | None = None
    adult: bool | None = None
    video: bool | None = None
    genres: list[NamedId]
    vote_average: Annotated[float, Field(ge=0, le=10)] | None = None
    vote_count: Annotated[int, Field(strict=True, ge=0)] | None = None
    popularity: Nonnegative | None = None
    poster_path: Annotated[str, Field(max_length=500)] | None = None
    credits: CreditsPayload
    keywords: KeywordsPayload

    @field_validator("release_date", mode="before")
    @classmethod
    def empty_date(cls, value):
        return None if value == "" else value

class DiscoverItem(Payload):
    id: SourceId

class DiscoveryPayload(Payload):
    page: Annotated[int, Field(strict=True, ge=1, le=500)]
    total_pages: Annotated[int, Field(strict=True, ge=0)]
    results: list[DiscoverItem]

class ImagesPayload(Payload):
    secure_base_url: str
    poster_sizes: list[str]
    profile_sizes: list[str]

    @field_validator("secure_base_url")
    @classmethod
    def trusted_cdn(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.hostname != "image.tmdb.org" or parsed.port not in (None,443) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/t/p/":
            raise ValueError("Unexpected TMDB image configuration")
        return value

    @field_validator("poster_sizes", "profile_sizes")
    @classmethod
    def sizes(cls, values):
        if not values or any(not re.fullmatch(r"original|[wh][1-9][0-9]{0,4}", s) for s in values):
            raise ValueError("Unexpected TMDB image size")
        return values

class ConfigurationPayload(Payload):
    images: ImagesPayload

class ReviewOverride(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    decision: Literal["eligible", "excluded"]
    reason: Annotated[str, Field(min_length=10, max_length=500)]
    reviewer: Annotated[str, Field(min_length=1, max_length=100)]
    confirmed_narrative_feature: bool = False
    verified_runtime_minutes: Annotated[int, Field(strict=True, ge=60, le=2000)] | None = None

def image_url(configuration: dict, path: str | None, kind: str) -> str | None:
    if not path or not re.fullmatch(r"/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp)", path):
        return None
    if kind not in ("poster", "profile"):
        raise ValueError("Unknown image kind")
    config = ImagesPayload.model_validate(configuration)
    sizes = getattr(config, kind + "_sizes")
    preferred = "w342" if kind == "poster" else "w185"
    size = preferred if preferred in sizes else ("original" if "original" in sizes else sizes[0])
    return config.secure_base_url + size + path
