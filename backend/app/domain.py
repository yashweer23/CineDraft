"""Stable contract vocabulary. These definitions do not execute game actions."""
from enum import StrEnum

class Role(StrEnum):
    DIRECTOR = "director"
    ACTOR = "actor"
    WRITER = "writer"
    CINEMATOGRAPHER = "cinematographer"
    COMPOSER = "composer"

class Slot(StrEnum):
    DIRECTOR = "director"
    LEAD = "lead"
    CO_LEAD = "co_lead"
    SUPPORTING_1 = "supporting_1"
    SUPPORTING_2 = "supporting_2"
    WRITER = "writer"
    CINEMATOGRAPHER = "cinematographer"
    COMPOSER = "composer"

SLOT_ROLES = {slot: Role.ACTOR if slot in (Slot.LEAD, Slot.CO_LEAD, Slot.SUPPORTING_1, Slot.SUPPORTING_2) else Role(slot.value) for slot in Slot}

class DraftStatus(StrEnum):
    AWAITING_PICK = "awaiting_pick"
    RECAST_AVAILABLE = "recast_available"
    RECAST_PREVIEW = "recast_preview"
    REVIEW_LOCKED = "review_locked"
    PRODUCTION_FINALIZED = "production_finalized"
    SIMULATION_RUNNING = "simulation_running"
    SIMULATION_FAILED = "simulation_failed"
    RESULTS_AVAILABLE = "results_available"
    ABANDONED = "abandoned"

class Command(StrEnum):
    CREATE = "create"
    PICK = "pick"
    REROLL = "reroll"
    PREVIEW_RECAST = "preview_recast"
    CANCEL_RECAST = "cancel_recast"
    CONFIRM_RECAST = "confirm_recast"
    FINALIZE = "finalize"
    RELEASE = "release"
    RETRY_SIMULATION = "retry_simulation"
    ABANDON = "abandon"

TIERS = {"indie": 10_000_000, "studio": 50_000_000, "blockbuster": 200_000_000}
GENRES = {"action": "Action", "adventure": "Adventure", "comedy": "Comedy", "crime": "Crime", "drama": "Drama", "horror": "Horror", "mystery": "Mystery", "romance": "Romance", "science_fiction": "Science Fiction", "thriller": "Thriller"}
