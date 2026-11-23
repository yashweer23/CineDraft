import copy
import json
from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.contracts import (Budget, CreateDraftRequest, PickRequest, CandidateCard,
                           ResultView, VersionBundle)
from app.repository import canonical_hash
from scripts.export_contracts import proposed_spec


def budget():
    return dict(tier="indie", total_budget_usd=10_000_000, reserve_usd=3_500_000,
                talent_budget_usd=6_500_000, talent_spend_usd=6_500_000, talent_remaining_usd=0)

@pytest.mark.parametrize("bad", [1.5, "6500000", True, -1])
def test_money_is_strict_integer_usd(bad):
    data = budget()
    data["talent_spend_usd"] = bad
    with pytest.raises(ValidationError):
        Budget(**data)

def test_exact_affordability_and_budget_reconciliation():
    assert Budget(**budget()).talent_remaining_usd == 0
    data = budget()
    data["reserve_usd"] -= 1
    with pytest.raises(ValidationError):
        Budget(**data)

def test_requests_reject_client_prices_seeds_and_negative_revisions():
    base = dict(request_id=uuid4(), genre_id="crime", tier="indie")
    for forbidden in ["seed", "pricing_id", "fee_usd", "owner_key_hash"]:
        with pytest.raises(ValidationError):
            CreateDraftRequest(**base, **{forbidden: "client supplied"})
    with pytest.raises(ValidationError):
        PickRequest(request_id=uuid4(), expected_revision=-1, offer_id=uuid4(), person_id=uuid4())

def test_notable_works_deduplicate_and_cap_five():
    versions = VersionBundle(**{key: "fixture:v1" for key in VersionBundle.model_fields})
    work = dict(movie_id=uuid4(), title="Fixture Film", year=None, credited_jobs=["Director"], poster_path=None, audience_rating=None, vote_count=None, source="fixture")
    card = dict(person_id=uuid4(), name="Fixture Person", role="director", hiring_fee_usd=150000,
                source="fixture", talent_strength=None, genre_fit=None, specialties=[],
                coverage="Fixture", notable_works=[work], versions=versions)
    assert CandidateCard(**card).notable_works[0].audience_rating is None
    card["notable_works"] = [work, work]
    with pytest.raises(ValidationError): CandidateCard(**card)
    card["notable_works"] = [dict(work, movie_id=uuid4()) for _ in range(6)]
    with pytest.raises(ValidationError): CandidateCard(**card)

def test_result_reconciles_profit_and_four_weeks():
    data = dict(draft_id=uuid4(), input_hash="a"*64, simulation_id=uuid4(),
                simulation_version="fixture:v1", synthetic=True, critics=60, audience=60,
                studio_score=60, production_cost_usd=10, marketing_usd=2, worldwide_gross_usd=20,
                studio_receipts_usd=10, profit_usd=-2, weekly_gross_usd=[8,6,4,2], explanation={})
    assert ResultView(**data).profit_usd == -2
    for changes in [{"profit_usd": 0}, {"weekly_gross_usd": [8,6,4,3]}]:
        with pytest.raises(ValidationError): ResultView(**(data | changes))

def test_hash_is_order_independent_and_rejects_nan():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})
    with pytest.raises(ValueError): canonical_hash({"a": float("nan")})

def test_exported_contract_is_current_and_private_drafts_require_bearer():
    current = proposed_spec()
    saved = json.loads((Path(__file__).resolve().parents[2] / "contracts/openapi.proposed.json").read_text())
    assert current == saved
    assert len(current["paths"]) == 15
    for path, operations in current["paths"].items():
        for op in operations.values():
            assert op["x-implementation-status"] == "planned"
            if "/drafts" in path:
                assert op["security"] == [{"HTTPBearer": []}]
    assert "ContractError" in current["components"]["schemas"]

def test_release_requires_authentication():
    from fastapi.testclient import TestClient
    from app.main import create_app
    from test_foundation import FakeDatabase, settings
    with TestClient(create_app(settings(), FakeDatabase())) as client:
        assert client.post("/api/v1/drafts/00000000-0000-0000-0000-000000000001/release", json={}).status_code == 401
        assert "/api/v1/drafts/{draft_id}/release" in client.get("/api/openapi.json").json()["paths"]


def test_frozen_snapshot_requires_complete_unique_roster_and_matching_cards():
    from app.contracts import FrozenInputs
    from app.domain import Slot, SLOT_ROLES
    versions = {key: "fixture:v1" for key in VersionBundle.model_fields}
    picks, cards = [], []
    for slot in Slot:
        person_id = str(uuid4())
        picks.append(dict(slot=slot.value, person_id=person_id, locked_fee_usd=100000, offer_id=str(uuid4())))
        cards.append(dict(person_id=person_id, name="Fixture Person", role=SLOT_ROLES[slot].value,
                          hiring_fee_usd=100000, source="fixture", talent_strength=None, genre_fit=None,
                          specialties=[], coverage="Synthetic", notable_works=[], versions=versions))
    money = budget() | {"talent_spend_usd": 800000, "talent_remaining_usd": 5700000}
    data = dict(synthetic=True, seed="fixture:seed", rules_configuration={}, scoring_configuration={}, cards=cards,
                draft=dict(draft_id=str(uuid4()), status="production_finalized", genre_id="drama", revision=9,
                           budget=money, picks=picks, current_offer=None, rerolls_used=0, recasts_used=0, versions=versions))
    assert FrozenInputs(**data).draft.budget.talent_spend_usd == 800000
    for scenario in ["duplicate", "missing", "wrong_fee", "wrong_version", "unfinished", "wrong_source"]:
        changed = copy.deepcopy(data)
        if scenario == "duplicate": changed["draft"]["picks"][1]["person_id"] = picks[0]["person_id"]
        if scenario == "missing": changed["draft"]["picks"].pop()
        if scenario == "wrong_fee": changed["cards"][0]["hiring_fee_usd"] = 200000
        if scenario == "wrong_version": changed["cards"][0]["versions"] = versions | {"pricing_id": "fixture:other"}
        if scenario == "unfinished": changed["draft"]["status"] = "recast_available"
        if scenario == "wrong_source": changed["cards"][0]["source"] = "tmdb"
        with pytest.raises(ValidationError): FrozenInputs(**changed)


def test_constraint_names_do_not_collide_within_a_table():
    # Multiple composite uniqueness rules share their first column. Naming them
    # only after that column can generate duplicate PostgreSQL index names.
    from app.models import Base
    for table in Base.metadata.tables.values():
        names = [str(c.name) for c in table.constraints if c.name]
        assert len(names) == len(set(names)), table.name
