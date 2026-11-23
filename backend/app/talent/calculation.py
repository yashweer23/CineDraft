"""Pure Phase 1 formulas. Decimal intermediates; six-place stored features."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Mapping
from app.domain import GENRES, Role, TIERS
from app.repository import canonical_hash

D = Decimal
FEATURE_VERSION = "talent-1.0"
RANKING_VERSION = "notability-1.0"
PRICING_VERSION = "fictional-fees-1.0"
PRECISION = 50
LIMITS = {"director": (150_000, 20_000_000), "actor": (100_000, 30_000_000),
          "writer": (125_000, 5_000_000), "cinematographer": (100_000, 4_000_000),
          "composer": (75_000, 6_000_000)}
FEATURE_PARAMETERS = {
    "schema_version": FEATURE_VERSION, "ranking_version": RANKING_VERSION,
    "film_prior_weight": 500, "person_prior_films": 3, "fallback_catalog_rating": "6.0",
    "experience_cap_films": 30, "versatility_cap_genres": 6, "genre_prior_films": 5,
    "missing_genre_prior": "0.5", "strength_weights": ["0.8", "0.2"],
    "notability_weights": ["0.75", "0.15", "0.08", "0.02"], "vote_signal_cap": 100000,
    "missing_person_popularity_appeal": 50, "missing_person_popularity_price": 0,
    "percentiles": "average zero-based rank / (observed count - 1); singleton 0.5",
    "genre_prior_denominator": "distinct person/movie pairs per role",
    "notability_ties": "unrounded score desc, effective votes desc, source asc, numeric TMDB ID asc or fixture key asc, UUID asc",
    "arithmetic_precision": PRECISION, "stored_decimal_places": 6, "rounding": "ROUND_HALF_UP",
}
PRICING_PARAMETERS = {"schema_version": PRICING_VERSION, "input_feature_version": FEATURE_VERSION,
    "weights": ["0.45", "0.35", "0.20"], "exponent": 2, "rounding_increment_usd": 25000,
    "rounding": "ROUND_HALF_UP", "limits_usd": {r: list(v) for r, v in LIMITS.items()},
    "inputs": "stored six-decimal strength, pricing popularity percentile, experience",
    "currency": "USD", "fee_is_fictional": True, "tier_independent": True}

@dataclass(frozen=True)
class Film:
    id: str
    source: str
    source_key: str
    title: str
    release_date: date | None = None
    rating: Decimal | None = None
    votes: int | None = None
    popularity: Decimal | None = None
    poster_path: str | None = None
    language: str | None = "en"
    genres: frozenset[str] = frozenset()
    eligible: bool = True

@dataclass(frozen=True)
class Person:
    id: str
    popularity: Decimal | None = None

@dataclass(frozen=True)
class Credit:
    person_id: str
    movie_id: str
    role: str | None
    job: str


def number(value):
    return float(D(value).quantize(D("0.000001"), rounding=ROUND_HALF_UP))


def percentiles(values: Mapping[str, Decimal | None]):
    """log(1+x) is strictly increasing: ranking x gives the same percentiles."""
    observed = sorted((D(v), k) for k, v in values.items() if v is not None)
    result = {}; n = len(observed); start = 0
    while start < n:
        end = start + 1
        while end < n and observed[end][0] == observed[start][0]: end += 1
        rank = D("0.5") if n == 1 else D(start + end - 1) / (2 * D(n - 1))
        for _, key in observed[start:end]: result[key] = rank
        start = end
    return result


def valid_reception(film):
    return film.rating is not None and film.votes is not None and film.votes > 0


def adjusted_reception(film, prior):
    if not valid_reception(film): return prior
    return (D(film.votes) * film.rating + 500 * prior) / (film.votes + 500)


def source_order(film):
    # Source keys are numeric only for TMDB. Synthetic identities stay strings.
    return (film.source, int(film.source_key) if film.source == "tmdb" else film.source_key, film.id)


def _validate(films, people, credits):
    if len({f.id for f in films}) != len(films) or len({p.id for p in people}) != len(people):
        raise ValueError("Duplicate input identity")
    for f in films:
        if f.source not in ("tmdb", "fixture") or (f.source == "tmdb" and (not f.source_key.isdecimal() or int(f.source_key) < 1)):
            raise ValueError("Invalid source identity")
        if f.rating is not None and (not f.rating.is_finite() or not 0 <= f.rating <= 10):
            raise ValueError("Invalid source rating")
        if f.votes is not None and (type(f.votes) is not int or f.votes < 0):
            raise ValueError("Invalid source votes")
        if not f.genres.issubset(GENRES): raise ValueError("Unknown game genre")
    for v in [f.popularity for f in films] + [p.popularity for p in people]:
        if v is not None and (not v.is_finite() or v < 0): raise ValueError("Invalid popularity")
    pids = {p.id for p in people}; mids = {f.id for f in films}
    if any(c.person_id not in pids or c.movie_id not in mids for c in credits):
        raise ValueError("Credit references missing source snapshot")


def build_features(films: list[Film], people: list[Person], credits: list[Credit]):
    _validate(films, people, credits)
    with localcontext() as ctx:
        ctx.prec = PRECISION; ctx.rounding = ROUND_HALF_UP
        return _build_features(films, people, credits)


def _build_features(films, people, credits):
    eligible = {f.id: f for f in sorted(films, key=lambda f: f.id) if f.eligible}
    person_by_id = {p.id: p for p in people}
    observed = [f.rating for f in eligible.values() if valid_reception(f)]
    prior = sum(observed, D(0)) / len(observed) if observed else D(6)
    movie_pop = percentiles({f.id: f.popularity for f in eligible.values()})
    grouped = defaultdict(lambda: defaultdict(set))
    for c in credits:
        if c.movie_id in eligible and c.role in LIMITS:
            grouped[(c.person_id, c.role)][c.movie_id].add(c.job)
    if not grouped: raise ValueError("No eligible mapped role credits in the sealed dataset")
    role_pairs = {r: [(pid, mid) for (pid, role), works in grouped.items() if role == r for mid in works] for r in LIMITS}
    role_pop = {r: percentiles({pid: person_by_id[pid].popularity for pid, _ in role_pairs[r]}) for r in LIMITS}
    genre_priors = {}; gaps = []
    for role, pairs in role_pairs.items():
        genre_priors[role] = {}
        for genre in GENRES:
            count = sum(genre in eligible[mid].genres for _, mid in pairs)
            genre_priors[role][genre] = D(count) / len(pairs) if count else D("0.5")
            if not count: gaps.append({"role": role, "genre": genre})
    ranked = {}
    for mid, f in eligible.items():
        votes = f.votes if valid_reception(f) else 0
        b = adjusted_reception(f, prior)
        v = min(D(1), D(1 + votes).ln() / D(100001).ln())
        p = movie_pop.get(mid, D(0))
        completeness = D(sum([bool(f.release_date), bool(f.poster_path), valid_reception(f), bool(f.language)])) / 4
        terms = {"reception": D("0.75") * b / 10, "vote_support": D("0.15") * v,
                 "visibility": D("0.08") * p, "completeness": D("0.02") * completeness}
        ranked[mid] = (sum(terms.values()), votes, b, terms)
    profiles = []
    for (pid, role), jobs in sorted(grouped.items()):
        works = [eligible[mid] for mid in sorted(jobs)]
        rated = [f for f in works if valid_reception(f)]
        n = len(works)
        reception = 10 * (sum((adjusted_reception(f, prior) for f in rated), D(0)) + 3 * prior) / (len(rated) + 3)
        experience = 100 * min(D(1), D(1 + n).ln() / D(31).ln())
        genres = set().union(*(f.genres for f in works))
        versatility = 100 * min(D(1), D(len(genres)) / 6)
        pop = role_pop[role].get(pid)
        strength = D("0.8") * reception + D("0.2") * experience
        counts = {g: sum(g in f.genres for f in works) for g in GENRES}
        genre_fit = {g: 100 * (counts[g] + 5 * genre_priors[role][g]) / (n + 5) for g in GENRES}
        years = [f.release_date.year for f in works if f.release_date]
        ordered = sorted(works, key=lambda f: (-ranked[f.id][0], -ranked[f.id][1], source_order(f)))
        notable = []
        for rank, f in enumerate(ordered[:5], 1):
            score, votes, b, terms = ranked[f.id]
            notable.append({"movie_id": f.id, "rank": rank, "credited_jobs": sorted(jobs[f.id]),
                "notability": number(score), "adjusted_reception": number(b),
                "reception_available": valid_reception(f), "effective_votes": votes,
                "components": {k: number(v) for k, v in terms.items()}})
        attributes = {"schema_version": FEATURE_VERSION, "talent_strength": number(strength),
            "reception": number(reception), "experience": number(experience), "versatility": number(versatility),
            "popularity_percentile": number(pop * 100) if pop is not None else None,
            "appeal_popularity": number(pop * 100 if pop is not None else D(50)),
            "pricing_popularity": number(pop * 100 if pop is not None else D(0)),
            "genre_fit": {g: number(v) for g, v in genre_fit.items()},
            "specialties": sorted(genres, key=lambda g: (-counts[g], -genre_fit[g], g))[:3],
            "career_span_years": max(years) - min(years) + 1 if years else None,
            "coverage": {"scope": "eligible imported catalog only", "eligible_movies": n,
                "rated_movies": len(rated), "level": "low" if n < 3 else "moderate" if n < 8 else "broader",
                "missing_person_popularity": pop is None, "reception_prior_only": not rated}}
        evidence = {"movie_ids": sorted(jobs), "rated_movie_ids": sorted(f.id for f in rated),
            "catalog_rating_prior": str(prior), "catalog_rating_prior_is_fallback": not observed,
            "genre_counts": counts, "genre_priors": {g: str(v) for g, v in genre_priors[role].items()},
            "genre_catalog_gaps": [g for g in GENRES if {"role": role, "genre": g} in gaps],
            "reception_contributions": [{"movie_id": f.id, "adjusted_reception": number(adjusted_reception(f, prior))} for f in rated],
            "notable_works": notable, "ranking_version": RANKING_VERSION,
            "strength_contributions": {"reception": number(D("0.8") * reception), "experience": number(D("0.2") * experience)}}
        profiles.append({"person_id": pid, "role": role, "attributes": attributes, "evidence": evidence})
    report = {"profiles": len(profiles), "people": len({p["person_id"] for p in profiles}),
        "eligible_movies": len(eligible), "rated_movies": len(observed), "catalog_rating_prior": str(prior),
        "catalog_rating_prior_is_fallback": not observed,
        "role_people": {r: len({pid for pid, _ in role_pairs[r]}) for r in LIMITS},
        "genre_catalog_gaps": gaps, "low_coverage_profiles": sum(p["attributes"]["coverage"]["level"] == "low" for p in profiles),
        "playable": False, "note": "Phase 7 exact assignment and offer coverage checks are still required."}
    inputs = {"films": [{"id": f.id, "source": f.source, "key": f.source_key, "title": f.title,
        "date": f.release_date.isoformat() if f.release_date else None, "rating": str(f.rating) if f.rating is not None else None,
        "votes": f.votes, "popularity": str(f.popularity) if f.popularity is not None else None,
        "poster_path": f.poster_path, "language": f.language, "genres": sorted(f.genres), "eligible": f.eligible} for f in sorted(films, key=lambda f: f.id)],
        "people": [{"id": p.id, "popularity": str(p.popularity) if p.popularity is not None else None} for p in sorted(people, key=lambda p: p.id)],
        "credits": sorted({(c.person_id, c.movie_id, c.role or "", c.job) for c in credits})}
    return {"parameters": FEATURE_PARAMETERS, "input_hash": canonical_hash(inputs), "profiles": profiles, "report": report}


def round_fee(raw: Decimal, floor: int, ceiling: int):
    rounded = int((raw / 25000).quantize(D(1), rounding=ROUND_HALF_UP)) * 25000
    return max(floor, min(ceiling, rounded))


def price_profile(role, attributes):
    if attributes.get("schema_version") != FEATURE_VERSION: raise ValueError("Unsupported feature schema")
    values = [D(str(attributes[k])) for k in ("talent_strength", "pricing_popularity", "experience")]
    if any(not v.is_finite() or not 0 <= v <= 100 for v in values): raise ValueError("Feature outside 0–100")
    with localcontext() as ctx:
        ctx.prec = PRECISION; ctx.rounding = ROUND_HALF_UP
        z = sum(w * v for w, v in zip([D("0.45"), D("0.35"), D("0.20")], values)) / 100
        floor, ceiling = LIMITS[role]
        raw = floor + (ceiling - floor) * z * z
        return {"fee_usd": round_fee(raw, floor, ceiling), "explanation": {
            "inputs": dict(zip(["talent_strength", "pricing_popularity", "experience"], map(number, values))),
            "z": number(z), "raw_fee_usd": str(raw), "floor_usd": floor, "ceiling_usd": ceiling,
            "rounding_increment_usd": 25000, "rounding": "ROUND_HALF_UP", "fee_is_fictional": True}}


def build_prices(profiles):
    rows = [{"person_id": p["person_id"], "role": p["role"], **price_profile(p["role"], p["attributes"])} for p in profiles]
    rows.sort(key=lambda p: (p["person_id"], p["role"]))
    by_role = {r: sorted(row["fee_usd"] for row in rows if row["role"] == r) for r in LIMITS}
    missing = [r for r, fees in by_role.items() if len(fees) < (4 if r == "actor" else 1)]
    lower = None if missing else sum(sum(fees[:4]) if r == "actor" else fees[0] for r, fees in by_role.items())
    report = {"fee_is_fictional": True, "currency": "USD", "playable": False,
        "role_prices": {r: {"count": len(fees), "min_usd": fees[0] if fees else None, "max_usd": fees[-1] if fees else None} for r, fees in by_role.items()},
        "missing_roster_roles": missing, "optimistic_roster_lower_bound_usd": lower,
        "lower_bound_note": "Four distinct actors plus one cheapest fee per other role; a person may overlap across roles. This is not a feasible assignment.",
        "tiers": {tier: {"talent_budget_usd": total * 65 // 100,
            "diagnostic": "insufficient_role_counts" if missing else "lower_bound_exceeds_budget" if lower > total * 65 // 100 else "needs_exact_assignment_check",
            "enabled": False} for tier, total in TIERS.items()}}
    return {"parameters": PRICING_PARAMETERS, "rows": rows, "report": report}
