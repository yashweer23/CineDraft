"""Inventory queries must work on PostgreSQL; no SQLite fallback."""
import pytest
from sqlalchemy.orm import Session
from app.drafting.catalog import availability
from app.drafting.schemas import CatalogAvailability
from app.validation.http_benchmark import inventory
from test_persistence import database
from test_draft_integration import game
pytestmark=pytest.mark.integration

def test_benchmark_inventory_matches_real_catalog(game):
    c,_,_=game
    with Session(c) as s:
        result=inventory(s,CatalogAvailability.model_validate(availability(c)))
    assert result['people']==22 and result['movies']==1 and result['person_roles']==23
    assert result['draft_count']==1 and result['migration']=='0009_phase15'


def test_benchmark_rejects_mismatched_database_catalog(game):
    c,_,_=game;catalog=CatalogAvailability.model_validate(availability(c));catalog.dataset_id='fixture:wrong'
    with Session(c) as s,pytest.raises(ValueError,match='do not match'):inventory(s,catalog)
