"""Versioned game policy; TMDB supplies metadata, not eligibility or talent scores."""
from datetime import date
import re
from app.repository import canonical_hash
from app.tmdb.payloads import MoviePayload, ReviewOverride

SCOPE_VERSION = "english-narrative-1.0"
ROLE_VERSION = "exact-credits-1.0"
POLICY_VERSION = "phase4-1.0"
GENRE_MAP = {28:"action",12:"adventure",35:"comedy",80:"crime",18:"drama",27:"horror",9648:"mystery",10749:"romance",878:"science_fiction",53:"thriller"}
JOBS = {"Director":"director", "Writer":"writer", "Screenplay":"writer", "Director of Photography":"cinematographer", "Original Music Composer":"composer"}
FORMAT_FLAGS = {"stand-up comedy", "stand-up", "stand up comedy", "concert", "concert film", "live performance", "filmed theater", "filmed theatre", "archive footage", "compilation"}

def credit_role(kind, credit):
    if kind == "crew":
        return JOBS.get(credit.job), "exact job" if credit.job in JOBS else "unmapped crew job"
    label = (credit.character or "").strip()
    if not label:
        return None, "acting character missing; review required"
    lower = label.casefold()
    if re.search(r"\b(archive|archival|self|himself|herself|themselves)\b", lower):
        return None, "self/archival or ambiguous acting credit excluded"
    if re.search(r"\b(uncredited|cameo)\b", lower):
        return None, "uncredited/cameo label requires review"
    if re.search(r"\b(stunt|stunts|stand-in)\b", lower):
        return None, "stunt/stand-in credit excluded"
    return "actor", "narrative cast credit"

def classify(movie: MoviePayload, cutoff: date, override: ReviewOverride | None = None):
    hard, review = [], []
    genre_ids = {g.id for g in movie.genres}
    if movie.original_language != "en": hard.append("original_language_not_english")
    if movie.status != "Released": hard.append("not_released")
    if movie.release_date and movie.release_date > cutoff: hard.append("after_cutoff")
    if not movie.release_date: review.append("release_date_missing")
    if movie.runtime is None or movie.runtime == 0: review.append("runtime_unknown")
    elif movie.runtime < 60: hard.append("runtime_under_60")
    if 99 in genre_ids: hard.append("documentary_genre")
    if 10770 in genre_ids: hard.append("tv_movie_genre")
    if movie.adult is True: hard.append("adult_flag")
    if movie.video is True: review.append("video_flag_format_review")
    if movie.adult is None: review.append("adult_flag_missing")
    flags = sorted({k.name.casefold() for k in movie.keywords.keywords} & FORMAT_FLAGS)
    if flags: review.append("format_keywords:" + ",".join(flags))
    # Keywords may describe a fictional plot; they are review flags, not automatic proof.
    cast_roles = [credit_role("cast", c)[0] for c in movie.credits.cast]
    if not cast_roles or not any(cast_roles): review.append("no_verified_narrative_cast")
    effective_runtime = movie.runtime or None
    if override and override.decision == "excluded":
        return {"status":"excluded", "reasons":hard+review+["manual_exclusion"], "runtime":effective_runtime, "override":override.model_dump()}
    if hard:
        return {"status":"excluded", "reasons":hard+review, "runtime":effective_runtime, "override":override.model_dump() if override else None}
    if override and override.decision == "eligible":
        if not override.confirmed_narrative_feature:
            raise ValueError("Eligible override must explicitly confirm a narrative feature")
        if "runtime_unknown" in review and override.verified_runtime_minutes:
            effective_runtime = override.verified_runtime_minutes
            review.remove("runtime_unknown")
        review = [r for r in review if not (r.startswith("format_keywords:") or r == "video_flag_format_review")]
    return {"status":"review" if review else "eligible", "reasons":review or ["scope_checks_passed"], "runtime":effective_runtime, "override":override.model_dump() if override else None}

def normalize_credits(movie: MoviePayload):
    seen, rows, duplicate_count = {}, [], 0
    for kind, entries in [("cast", movie.credits.cast), ("crew", movie.credits.crew)]:
        for c in entries:
            job = "Actor" if kind == "cast" else (c.job or "Unknown")
            identity = {"person":c.id,"movie":movie.id,"kind":kind,"job":job,"character":c.character}
            key = "tmdb-credit:" + c.credit_id if c.credit_id else "composite:" + canonical_hash(identity)
            role, reason = credit_role(kind, c)
            row = {"person_source_id":c.id,"movie_source_id":movie.id,"dedupe_key":key,
                   "source_credit_id":c.credit_id,"kind":kind,"job":job,"department":c.department,
                   "character":c.character,"cast_order":c.order,"role":role,"mapping_reason":reason}
            if key in seen:
                if seen[key] != row:
                    raise ValueError("Conflicting duplicate source credit; inspect checkpoint before publishing")
                duplicate_count += 1
                continue
            seen[key]=row; rows.append(row)
    return rows, duplicate_count
