"""Explicit synthetic records for a local persistence exercise, never TMDB data."""
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy.orm import Session
from app import models as m
from app.contracts import (Budget, CandidateCard, DraftView, FrozenInputs, PickView,
                           ResultView, VersionBundle)
from app.domain import Slot, SLOT_ROLES, GENRES
from app.repository import canonical_hash, save_snapshot, save_result

DATASET = "fixture:dataset-v1"
DRAFT_ID = uuid5(NAMESPACE_URL, "cinedraft:fixture:phase3:draft-v1")

def fixture_id(key):
    return uuid5(NAMESPACE_URL, "cinedraft:fixture:" + key)

def add(session, row):
    session.add(row)
    session.flush()
    return row

def seal(session, row):
    row.sealed = True
    session.flush()

def seed_fixture(session: Session) -> dict:
    """Transaction supplied by caller. Re-running a complete fixture is a no-op."""
    if session.get(m.DatasetVersion, DATASET):
        if not session.get(m.Result, DRAFT_ID):
            raise ValueError("Incomplete fixture exists; inspect it instead of overwriting")
        return {"synthetic": True, "dataset_id": DATASET, "draft_id": str(DRAFT_ID), "created": False}
    versions = VersionBundle(dataset_id=DATASET, feature_id="fixture:features-v1", pricing_id="fixture:pricing-v1", rules_id="fixture:rules-v1", scoring_id="fixture:scoring-v1", ranking_version="fixture:ranking-none", role_mapping_version="fixture:roles-v1", prng_version="fixture:recorded-offers-v1", simulation_version="fixture:handwritten-result-v1")
    config = {"synthetic": True, "purpose": "Phase 3 round-trip only", "members": [s.value for s in Slot]}
    dataset = add(session, m.DatasetVersion(id=DATASET, configuration=config, content_hash=canonical_hash(config), scope_version="fixture:scope-v1", role_mapping_version=versions.role_mapping_version, provenance={"source": "fixture", "tmdb_requests": 0}))
    for key, name in GENRES.items():
        if not session.get(m.Genre, key):
            add(session, m.Genre(id=key, name=name))
    movie_id = fixture_id("movie-v1")
    add(session, m.Movie(id=movie_id, source="fixture", source_key="fixture:movie-v1"))
    add(session, m.MovieSnapshot(dataset_id=DATASET, movie_id=movie_id, title="Fixture Film — Persistence Exercise", original_language="en", release_date=None, runtime_minutes=90, poster_path=None, audience_rating=None, vote_count=None, popularity=None, eligibility="eligible", eligibility_reason="Synthetic narrative-film test", provenance={"source": "fixture"}))
    add(session, m.MovieGenre(dataset_id=DATASET, movie_id=movie_id, genre_id="drama"))
    profiles = []
    jobs = {"director": "Director", "actor": "Actor", "writer": "Screenplay", "cinematographer": "Director of Photography", "composer": "Original Music Composer"}
    for slot in Slot:
        person_id = fixture_id("person-" + slot.value)
        add(session, m.Person(id=person_id, source="fixture", source_key="fixture:person-" + slot.value))
        add(session, m.PersonSnapshot(dataset_id=DATASET, person_id=person_id, name="Fixture " + slot.value.replace("_", " ").title(), profile_path=None, popularity=None, coverage={"synthetic": True, "eligible_movies": 1}))
        roles = [SLOT_ROLES[slot].value]
        if slot == Slot.DIRECTOR:
            roles.append("writer")  # One identity, two professional profiles.
        for role in roles:
            profiles.append((person_id, role))
            add(session, m.Credit(dataset_id=DATASET, person_id=person_id, movie_id=movie_id, dedupe_key="fixture:" + slot.value + ":" + role, source_credit_id=None, kind="cast" if role == "actor" else "crew", job=jobs[role], department="Acting" if role == "actor" else role.title(), character="Fictional character" if role == "actor" else None, cast_order=None, role=role, provenance={"source": "fixture", "verified": "synthetic fixture only"}))
    seal(session, dataset)
    feature = add(session, m.FeatureVersion(id=versions.feature_id, dataset_id=DATASET, ranking_version=versions.ranking_version, configuration=config, content_hash=canonical_hash(config)))
    for person_id, role in profiles:
        add(session, m.RoleFeature(feature_id=feature.id, dataset_id=DATASET, person_id=person_id, role=role, attributes={"synthetic": True, "talent_strength": None, "genre_fit": None}, evidence={"movie_ids": [str(movie_id)], "ranking_implemented": False}))
    seal(session, feature)
    pricing = add(session, m.PricingVersion(id=versions.pricing_id, feature_id=feature.id, configuration={"synthetic": True, "method": "handwritten fixture fees"}, content_hash=canonical_hash({"synthetic": True, "method": "handwritten fixture fees"})))
    fees = {"director": 150_000, "actor": 100_000, "writer": 125_000, "cinematographer": 100_000, "composer": 75_000}
    for person_id, role in profiles:
        add(session, m.RolePrice(pricing_id=pricing.id, feature_id=feature.id, person_id=person_id, role=role, fee_usd=fees[role]))
    seal(session, pricing)
    for cls, key in [(m.RulesVersion, versions.rules_id), (m.ScoringVersion, versions.scoring_id)]:
        row = add(session, cls(id=key, configuration=config, content_hash=canonical_hash(config)))
        seal(session, row)
    draft = add(session, m.Draft(id=DRAFT_ID, owner_key_hash=canonical_hash({"owner": "fixture only; not an access token"}), status="awaiting_pick", genre_id="drama", tier="indie", total_budget_usd=10_000_000, reserve_usd=3_500_000, talent_budget_usd=6_500_000, talent_spend_usd=0, seed="fixture:seed-v1", prng_version=versions.prng_version, dataset_id=DATASET, feature_id=feature.id, pricing_id=pricing.id, rules_id=versions.rules_id, scoring_id=versions.scoring_id, simulation_version=versions.simulation_version))
    cards, picks = [], []
    for i, slot in enumerate(Slot):
        person_id = fixture_id("person-" + slot.value)
        role = SLOT_ROLES[slot]
        card = CandidateCard(person_id=person_id, name="Fixture " + slot.value, role=role, hiring_fee_usd=fees[role], source="fixture", talent_strength=None, genre_fit=None, specialties=[], coverage="Synthetic: one fixture film", notable_works=[{"movie_id": movie_id, "title": "Fixture Film — Persistence Exercise", "year": None, "credited_jobs": [jobs[role]], "poster_path": None, "audience_rating": None, "vote_count": None, "source": "fixture"}], versions=versions)
        offer = add(session, m.Offer(id=fixture_id("offer-" + slot.value), draft_id=draft.id, slot=slot.value, kind="pick", revision=i, rng_position=i))
        add(session, m.OfferCandidate(offer_id=offer.id, person_id=person_id, position=1, fee_usd=fees[role], selectable=True, blocked_reason=None, card_snapshot=card.model_dump(mode="json")))
        seal(session, offer)
        add(session, m.Pick(draft_id=draft.id, slot=slot.value, person_id=person_id, offer_id=offer.id, locked_fee_usd=fees[role], picked_at_revision=i+1))
        body = {"request_id": str(fixture_id("request-" + slot.value)), "expected_revision": i, "offer_id": str(offer.id), "person_id": str(person_id)}
        add(session, m.ActionRecord(draft_id=draft.id, command="pick", request_id=fixture_id("request-" + slot.value), body_hash=canonical_hash(body), request_body=body, response_body={"synthetic": True, "revision": i+1}, response_status=200, revision_before=i, revision_after=i+1))
        cards.append(card)
        picks.append(PickView(slot=slot, person_id=person_id, offer_id=offer.id, locked_fee_usd=fees[role]))
    spend = sum(p.locked_fee_usd for p in picks)
    draft.revision = 9
    draft.talent_spend_usd = spend
    draft.status = "production_finalized"
    session.flush()
    body = {"request_id": str(fixture_id("finalize")), "expected_revision": 8}
    add(session, m.ActionRecord(draft_id=draft.id, command="finalize", request_id=fixture_id("finalize"), body_hash=canonical_hash(body), request_body=body, response_body={"synthetic": True, "revision": 9}, response_status=200, revision_before=8, revision_after=9))
    view = DraftView(draft_id=draft.id, status=draft.status, genre_id="drama", revision=9, budget=Budget(tier="indie", total_budget_usd=10_000_000, reserve_usd=3_500_000, talent_budget_usd=6_500_000, talent_spend_usd=spend, talent_remaining_usd=6_500_000-spend), picks=picks, current_offer=None, rerolls_used=0, recasts_used=0, versions=versions)
    snapshot = save_snapshot(session, FrozenInputs(synthetic=True, draft=view, seed=draft.seed, cards=cards, rules_configuration=config, scoring_configuration=config))
    production = 3_500_000 + spend
    marketing = production // 5
    save_result(session, ResultView(draft_id=draft.id, input_hash=snapshot.input_hash, simulation_id=fixture_id("simulation-v1"), simulation_version=versions.simulation_version, synthetic=True, critics=60, audience=60, studio_score=60, production_cost_usd=production, marketing_usd=marketing, worldwide_gross_usd=10_000_000, studio_receipts_usd=5_000_000, profit_usd=5_000_000-production-marketing, weekly_gross_usd=[4_000_000, 3_000_000, 2_000_000, 1_000_000], explanation={"synthetic": True, "note": "Handwritten arithmetic fixture; no simulator or scoring engine ran"}))
    draft.status = "results_available"
    session.flush()
    return {"synthetic": True, "dataset_id": DATASET, "draft_id": str(DRAFT_ID), "created": True, "people": 8, "role_profiles": 9, "talent_spend_usd": spend}
