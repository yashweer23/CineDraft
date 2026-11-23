"""Real PostgreSQL integration: isolated schema + rolled-back transaction per test."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models as m
from app.fixtures import seed_fixture, DRAFT_ID, DATASET, fixture_id
from app.repository import load_snapshot, replay_action, IdempotencyConflict

pytestmark = pytest.mark.integration

@pytest.fixture
def database():
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Real PostgreSQL required: run python -m scripts.run_integration")
    engine = create_engine(value, hide_parameters=True)
    assert engine.dialect.name == "postgresql", "SQLite cannot verify PostgreSQL constraints"
    with engine.connect() as connection:
        transaction = connection.begin()
        schema = "phase3_test_" + uuid4().hex
        connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        connection.execute(text('SET LOCAL search_path TO "' + schema + '"'))
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
        config.attributes["connection"] = connection
        try:
            command.upgrade(config, "head")
            # Sessions bound to this connection now use their own savepoints.
            # A service rollback must not undo the migrated schema itself.
            connection.begin_nested()
            try:
                yield connection, config
            finally:
                assert transaction.is_active and connection.in_transaction(), "Test rolled back the outer isolation transaction"
                assert connection.scalar(text("SELECT current_schema()")) == schema, "Test lost its isolated schema"
        finally:
            transaction.rollback()  # Includes the temporary schema; no user table is dropped.
    engine.dispose()


def test_migration_upgrade_downgrade_and_no_metadata_drift(database):
    connection, config = database
    command.upgrade(config, "head")
    assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0009_phase15"
    assert compare_metadata(MigrationContext.configure(connection), m.Base.metadata) == []
    command.downgrade(config, "base")
    assert not connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema=current_schema() AND table_name='people'"))
    command.upgrade(config, "head")


def test_roundtrip_multi_role_snapshot_and_result(database):
    with Session(database[0]) as session:
        first = seed_fixture(session)
        assert first["created"] and not seed_fixture(session)["created"]
        session.expire_all()
        snapshot = load_snapshot(session, DRAFT_ID)
        assert len(snapshot.draft.picks) == 8
        assert snapshot.draft.budget.talent_spend_usd == 850000
        roles = session.scalars(select(m.Credit.role).where(m.Credit.person_id == fixture_id("person-director"))).all()
        assert set(roles) == {"director", "writer"}
        assert session.get(m.Result, DRAFT_ID).outputs["synthetic"] is True
        action = session.scalar(select(m.ActionRecord).where(m.ActionRecord.command == "pick"))
        assert replay_action(session, DRAFT_ID, action.command, action.request_id, action.request_body).id == action.id
        with pytest.raises(IdempotencyConflict):
            replay_action(session, DRAFT_ID, action.command, action.request_id, {"changed": True})


@pytest.mark.parametrize("sql", [
    "UPDATE person_snapshots SET name='Edited'",
    "UPDATE dataset_versions SET sealed=false",
    "DELETE FROM results",
    "UPDATE draft_snapshots SET inputs='{}'::jsonb",
    "UPDATE drafts SET talent_spend_usd=6500001",
    "UPDATE drafts SET seed='changed'",
    "UPDATE picks SET locked_fee_usd=0",
    "INSERT INTO person_snapshots SELECT dataset_id, gen_random_uuid(), name, profile_path, popularity, coverage FROM person_snapshots LIMIT 1",
    "INSERT INTO action_records SELECT gen_random_uuid(), draft_id, command, request_id, body_hash, request_body, response_body, response_status, revision_before, revision_after, created_at FROM action_records LIMIT 1",
])
def test_invalid_writes_rejected(database, sql):
    with Session(database[0]) as session:
        seed_fixture(session)
        with pytest.raises(IntegrityError), session.begin_nested():
            session.execute(text(sql))
        assert load_snapshot(session, DRAFT_ID).synthetic


def test_duplicate_person_and_cross_draft_offer_rejected(database):
    with Session(database[0]) as session:
        seed_fixture(session)
        original = session.get(m.Draft, DRAFT_ID)
        fields = {column.name: getattr(original, column.name) for column in m.Draft.__table__.columns if column.name not in {"id", "created_at"}}
        fields.update(status="awaiting_pick", talent_spend_usd=0, revision=0)
        draft = m.Draft(**fields)
        session.add(draft); session.flush()
        director = fixture_id("person-director")
        for i, (slot, fee) in enumerate([("director", 150000), ("writer", 125000)]):
            offer = m.Offer(draft_id=draft.id, slot=slot, kind="pick", revision=i, rng_position=i)
            session.add(offer); session.flush()
            with pytest.raises(IntegrityError), session.begin_nested():
                session.add(m.OfferCandidate(offer_id=offer.id, person_id=director, position=1, fee_usd=fee+1, selectable=True, blocked_reason=None, card_snapshot={"synthetic": True}))
                session.flush()
            session.add(m.OfferCandidate(offer_id=offer.id, person_id=director, position=1, fee_usd=fee, selectable=True, blocked_reason=None, card_snapshot={"synthetic": True}))
            session.flush(); offer.sealed=True; session.flush()
            if i == 0:
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(m.Pick(draft_id=draft.id, slot=slot, person_id=director, offer_id=offer.id, locked_fee_usd=fee+1, picked_at_revision=1))
                    session.flush()
                session.add(m.Pick(draft_id=draft.id, slot=slot, person_id=director, offer_id=offer.id, locked_fee_usd=fee, picked_at_revision=1))
                session.flush()
            else:
                with pytest.raises(IntegrityError), session.begin_nested():
                    session.add(m.Pick(draft_id=draft.id, slot=slot, person_id=director, offer_id=offer.id, locked_fee_usd=fee, picked_at_revision=2))
                    session.flush()
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(m.Pick(draft_id=draft.id, slot="lead", person_id=fixture_id("person-lead"), offer_id=fixture_id("offer-lead"), locked_fee_usd=100000, picked_at_revision=2))
            session.flush()
