"""PostgreSQL persistence through Phase 7. Migrations, not create_all(), own DDL."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        ForeignKeyConstraint, Index, Integer, MetaData, Numeric,
                        String, UniqueConstraint, Uuid, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.domain import Role, Slot, DraftStatus, Command

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={"ix": "ix_%(table_name)s_%(column_0_name)s", "uq": "uq_%(table_name)s_%(column_0_N_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"})

def allowed(column, values, name):
    return CheckConstraint(column + " IN (" + ", ".join(repr(str(v)) for v in values) + ")", name=name)

class Identity:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(16))
    source_key: Mapped[str] = mapped_column(String(160))

class Person(Identity, Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("source", "source_key"), allowed("source", ["fixture", "tmdb"], "source"), CheckConstraint("(source = 'fixture' AND source_key LIKE 'fixture:%') OR (source = 'tmdb' AND source_key ~ '^[1-9][0-9]*$')", name="source_key"))

class Movie(Identity, Base):
    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("source", "source_key"), allowed("source", ["fixture", "tmdb"], "source"), CheckConstraint("(source = 'fixture' AND source_key LIKE 'fixture:%') OR (source = 'tmdb' AND source_key ~ '^[1-9][0-9]*$')", name="source_key"))

class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)

class Version:
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    configuration: Mapped[dict] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64))
    sealed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DatasetVersion(Version, Base):
    __tablename__ = "dataset_versions"
    scope_version: Mapped[str] = mapped_column(String(100))
    role_mapping_version: Mapped[str] = mapped_column(String(100))
    provenance: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"),)

class PersonSnapshot(Base):
    __tablename__ = "person_snapshots"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(240))
    profile_path: Mapped[str | None] = mapped_column(String(500))
    popularity: Mapped[Decimal | None] = mapped_column(Numeric(16, 6))
    coverage: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (CheckConstraint("popularity IS NULL OR popularity >= 0", name="popularity"),)

class MovieSnapshot(Base):
    __tablename__ = "movie_snapshots"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), primary_key=True)
    movie_id: Mapped[UUID] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    original_language: Mapped[str | None] = mapped_column(String(10))
    release_date: Mapped[date | None]
    runtime_minutes: Mapped[int | None]
    poster_path: Mapped[str | None] = mapped_column(String(500))
    audience_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    vote_count: Mapped[int | None]
    popularity: Mapped[Decimal | None] = mapped_column(Numeric(16, 6))
    eligibility: Mapped[str] = mapped_column(String(16))
    eligibility_reason: Mapped[str] = mapped_column(String(500))
    provenance: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (allowed("eligibility", ["eligible", "excluded", "review"], "eligibility"), CheckConstraint("audience_rating BETWEEN 0 AND 10", name="rating"), CheckConstraint("vote_count >= 0", name="votes"), CheckConstraint("runtime_minutes > 0", name="runtime"), CheckConstraint("popularity >= 0", name="popularity"))

class MovieGenre(Base):
    __tablename__ = "movie_genres"
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    movie_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    genre_id: Mapped[str] = mapped_column(ForeignKey("genres.id"), primary_key=True)
    __table_args__ = (ForeignKeyConstraint(["dataset_id", "movie_id"], ["movie_snapshots.dataset_id", "movie_snapshots.movie_id"]),)

class Credit(Base):
    __tablename__ = "credits"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(100))
    person_id: Mapped[UUID] = mapped_column(Uuid)
    movie_id: Mapped[UUID] = mapped_column(Uuid)
    dedupe_key: Mapped[str] = mapped_column(String(300))
    source_credit_id: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(8))
    job: Mapped[str] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(120))
    character: Mapped[str | None] = mapped_column(String(500))
    cast_order: Mapped[int | None]
    role: Mapped[str | None] = mapped_column(String(24))
    provenance: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (ForeignKeyConstraint(["dataset_id", "person_id"], ["person_snapshots.dataset_id", "person_snapshots.person_id"]), ForeignKeyConstraint(["dataset_id", "movie_id"], ["movie_snapshots.dataset_id", "movie_snapshots.movie_id"]), UniqueConstraint("dataset_id", "dedupe_key"), UniqueConstraint("dataset_id", "source_credit_id"), allowed("kind", ["cast", "crew"], "kind"), allowed("role", Role, "role"), CheckConstraint("cast_order >= 0", name="cast_order"), Index("ix_credits_person_role", "dataset_id", "person_id", "role"), Index("ix_credits_movie", "dataset_id", "movie_id"))

class FeatureVersion(Version, Base):
    __tablename__ = "feature_versions"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    ranking_version: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("id", "dataset_id"), CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"))

class RoleFeature(Base):
    __tablename__ = "role_features"
    feature_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(100))
    attributes: Mapped[dict] = mapped_column(JSONB)
    evidence: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (ForeignKeyConstraint(["feature_id", "dataset_id"], ["feature_versions.id", "feature_versions.dataset_id"]), ForeignKeyConstraint(["dataset_id", "person_id"], ["person_snapshots.dataset_id", "person_snapshots.person_id"]), allowed("role", Role, "role"))

class PricingVersion(Version, Base):
    __tablename__ = "pricing_versions"
    feature_id: Mapped[str] = mapped_column(ForeignKey("feature_versions.id"))
    __table_args__ = (UniqueConstraint("id", "feature_id"), CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"))

class RolePrice(Base):
    __tablename__ = "role_prices"
    pricing_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    feature_id: Mapped[str] = mapped_column(String(100))
    fee_usd: Mapped[int] = mapped_column(BigInteger)
    __table_args__ = (ForeignKeyConstraint(["pricing_id", "feature_id"], ["pricing_versions.id", "pricing_versions.feature_id"]), ForeignKeyConstraint(["feature_id", "person_id", "role"], ["role_features.feature_id", "role_features.person_id", "role_features.role"]), CheckConstraint("fee_usd >= 0", name="fee"))

class RulesVersion(Version, Base):
    __tablename__ = "rules_versions"
    __table_args__ = (CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"),)

class ScoringVersion(Version, Base):
    __tablename__ = "scoring_versions"
    __table_args__ = (CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"),)

class Draft(Base):
    __tablename__ = "drafts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_key_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(24), default="classic")
    genre_id: Mapped[str] = mapped_column(ForeignKey("genres.id"))
    tier: Mapped[str] = mapped_column(String(16))
    total_budget_usd: Mapped[int] = mapped_column(BigInteger)
    reserve_usd: Mapped[int] = mapped_column(BigInteger)
    talent_budget_usd: Mapped[int] = mapped_column(BigInteger)
    talent_spend_usd: Mapped[int] = mapped_column(BigInteger, default=0)
    rerolls_used: Mapped[int] = mapped_column(Integer, default=0)
    recasts_used: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[str] = mapped_column(String(128))
    prng_version: Mapped[str] = mapped_column(String(100))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    graph_id: Mapped[str | None] = mapped_column(String(100))
    feature_id: Mapped[str] = mapped_column(String(100))
    pricing_id: Mapped[str] = mapped_column(String(100))
    rules_id: Mapped[str] = mapped_column(ForeignKey("rules_versions.id"))
    scoring_id: Mapped[str] = mapped_column(ForeignKey("scoring_versions.id"))
    simulation_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(["graph_id", "dataset_id"], ["graph_versions.id", "graph_versions.dataset_id"], name="fk_drafts_graph_dataset"), ForeignKeyConstraint(["feature_id", "dataset_id"], ["feature_versions.id", "feature_versions.dataset_id"]), ForeignKeyConstraint(["pricing_id", "feature_id"], ["pricing_versions.id", "pricing_versions.feature_id"]), allowed("status", DraftStatus, "status"), allowed("mode", ["classic"], "mode"), CheckConstraint("(tier = 'indie' AND total_budget_usd = 10000000) OR (tier = 'studio' AND total_budget_usd = 50000000) OR (tier = 'blockbuster' AND total_budget_usd = 200000000)", name="tier_budget"), CheckConstraint("reserve_usd = total_budget_usd * 35 / 100 AND talent_budget_usd = total_budget_usd - reserve_usd", name="allocation"), CheckConstraint("talent_spend_usd BETWEEN 0 AND talent_budget_usd", name="spend"), CheckConstraint("rerolls_used BETWEEN 0 AND 2 AND recasts_used BETWEEN 0 AND 1 AND revision >= 0", name="counters"), CheckConstraint("owner_key_hash ~ '^[0-9a-f]{64}$'", name="owner"), Index("ix_drafts_owner_created", "owner_key_hash", "created_at"))

class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id"))
    slot: Mapped[str] = mapped_column(String(24))
    kind: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int]
    rng_position: Mapped[int] = mapped_column(BigInteger)
    sealed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    __table_args__ = (UniqueConstraint("id", "draft_id", name="uq_offers_id_draft"), UniqueConstraint("id", "draft_id", "slot"), UniqueConstraint("draft_id", "revision", "slot", "kind"), allowed("slot", Slot, "slot"), allowed("kind", ["pick", "recast"], "kind"), CheckConstraint("revision >= 0 AND rng_position >= 0", name="counters"))

class OfferCandidate(Base):
    __tablename__ = "offer_candidates"
    offer_id: Mapped[UUID] = mapped_column(ForeignKey("offers.id"), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"), primary_key=True)
    position: Mapped[int]
    fee_usd: Mapped[int] = mapped_column(BigInteger)
    selectable: Mapped[bool]
    blocked_reason: Mapped[str | None] = mapped_column(String(500))
    card_snapshot: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("offer_id", "position", name="uq_offer_candidate_position"), UniqueConstraint("offer_id", "person_id", "fee_usd", name="uq_offer_candidate_fee"), CheckConstraint("position BETWEEN 1 AND 3 AND fee_usd >= 0", name="bounds"), CheckConstraint("(selectable AND blocked_reason IS NULL) OR (NOT selectable AND blocked_reason IS NOT NULL)", name="reason"))

class Pick(Base):
    __tablename__ = "picks"
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id"), primary_key=True)
    slot: Mapped[str] = mapped_column(String(24), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("people.id"))
    offer_id: Mapped[UUID] = mapped_column(Uuid)
    locked_fee_usd: Mapped[int] = mapped_column(BigInteger)
    picked_at_revision: Mapped[int]
    __table_args__ = (UniqueConstraint("draft_id", "person_id"), ForeignKeyConstraint(["offer_id", "draft_id", "slot"], ["offers.id", "offers.draft_id", "offers.slot"]), ForeignKeyConstraint(["offer_id", "person_id", "locked_fee_usd"], ["offer_candidates.offer_id", "offer_candidates.person_id", "offer_candidates.fee_usd"]), CheckConstraint("locked_fee_usd >= 0 AND picked_at_revision > 0", name="bounds"), allowed("slot", Slot, "slot"))

class ActionRecord(Base):
    __tablename__ = "action_records"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id"))
    command: Mapped[str] = mapped_column(String(24))
    request_id: Mapped[UUID] = mapped_column(Uuid)
    body_hash: Mapped[str] = mapped_column(String(64))
    request_body: Mapped[dict] = mapped_column(JSONB)
    response_body: Mapped[dict] = mapped_column(JSONB)
    response_status: Mapped[int]
    revision_before: Mapped[int]
    revision_after: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("draft_id", "command", "request_id", name="uq_action_request"), UniqueConstraint("draft_id", "revision_after", name="uq_action_revision"), allowed("command", Command, "command"), CheckConstraint("revision_before >= 0 AND revision_after = revision_before + 1", name="revision"), CheckConstraint("response_status BETWEEN 200 AND 299", name="success"), CheckConstraint("body_hash ~ '^[0-9a-f]{64}$'", name="hash"))

class DraftSnapshot(Base):
    __tablename__ = "draft_snapshots"
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id"), primary_key=True)
    revision: Mapped[int]
    input_hash: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("draft_id", "input_hash"), CheckConstraint("input_hash ~ '^[0-9a-f]{64}$' AND revision >= 0", name="bounds"))

class Result(Base):
    __tablename__ = "results"
    draft_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    simulation_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    simulation_version: Mapped[str] = mapped_column(String(100))
    output_hash: Mapped[str] = mapped_column(String(64))
    outputs: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(["draft_id", "input_hash"], ["draft_snapshots.draft_id", "draft_snapshots.input_hash"]), CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'", name="hash"))


class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    dataset_id: Mapped[str] = mapped_column(String(100), unique=True)
    source: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="staging")
    plan: Mapped[dict] = mapped_column(JSONB)
    report: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (allowed("source", ["tmdb", "fixture"], "source"), allowed("status", ["staging", "published"], "status"), CheckConstraint("(source='tmdb' AND dataset_id LIKE 'tmdb:%') OR (source='fixture' AND dataset_id LIKE 'fixture:%')", name="namespace"))

class ImportResource(Base):
    __tablename__ = "import_resources"
    run_id: Mapped[UUID] = mapped_column(ForeignKey("import_runs.id"), primary_key=True)
    resource_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(80))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (allowed("state", ["ready", "failed"], "state"), CheckConstraint("(state='ready' AND payload IS NOT NULL AND payload_hash ~ '^[0-9a-f]{64}$' AND error_code IS NULL AND fetched_at IS NOT NULL) OR (state='failed' AND payload IS NULL AND payload_hash IS NULL AND error_code IS NOT NULL)", name="payload_state"))


class GraphVersion(Version, Base):
    __tablename__ = "graph_versions"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    algorithm_version: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("id", "dataset_id"), CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"))

class GraphNode(Base):
    __tablename__ = "graph_nodes"
    graph_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    person_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(100))
    film_count: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(["graph_id", "dataset_id"], ["graph_versions.id", "graph_versions.dataset_id"]),
        ForeignKeyConstraint(["dataset_id", "person_id"], ["person_snapshots.dataset_id", "person_snapshots.person_id"]),
        allowed("role", Role, "role"), CheckConstraint("film_count > 0", name="film_count"))

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    graph_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    person_a: Mapped[UUID] = mapped_column(Uuid)
    role_a: Mapped[str] = mapped_column(String(24))
    person_b: Mapped[UUID] = mapped_column(Uuid)
    role_b: Mapped[str] = mapped_column(String(24))
    shared_movie_count: Mapped[int] = mapped_column(Integer)
    bonus: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        ForeignKeyConstraint(["graph_id", "person_a", "role_a"], ["graph_nodes.graph_id", "graph_nodes.person_id", "graph_nodes.role"], name="fk_graph_edges_node_a"),
        ForeignKeyConstraint(["graph_id", "person_b", "role_b"], ["graph_nodes.graph_id", "graph_nodes.person_id", "graph_nodes.role"], name="fk_graph_edges_node_b"),
        UniqueConstraint("graph_id", "person_a", "role_a", "person_b", "role_b", name="uq_graph_edge_pair"),
        CheckConstraint("person_a < person_b", name="canonical_people"),
        CheckConstraint("edge_id ~ '^[0-9a-f]{64}$'", name="edge_hash"),
        CheckConstraint("shared_movie_count > 0 AND bonus = LEAST(12, 4 * shared_movie_count)", name="bonus"),
        Index("ix_graph_edges_count", "graph_id", "shared_movie_count"))

class GraphEvidence(Base):
    __tablename__ = "graph_evidence"
    graph_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    movie_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(100))
    jobs_a: Mapped[list] = mapped_column(JSONB)
    jobs_b: Mapped[list] = mapped_column(JSONB)
    __table_args__ = (
        ForeignKeyConstraint(["graph_id", "edge_id"], ["graph_edges.graph_id", "graph_edges.edge_id"]),
        ForeignKeyConstraint(["graph_id", "dataset_id"], ["graph_versions.id", "graph_versions.dataset_id"]),
        ForeignKeyConstraint(["dataset_id", "movie_id"], ["movie_snapshots.dataset_id", "movie_snapshots.movie_id"]),
        CheckConstraint("jsonb_typeof(jobs_a) = 'array' AND jsonb_array_length(jobs_a) > 0 AND jsonb_typeof(jobs_b) = 'array' AND jsonb_array_length(jobs_b) > 0", name="jobs"))


class GuestSession(Base):
    __tablename__ = 'guest_sessions'
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64),unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'",name='hash'),)

class DraftCatalog(Version,Base):
    __tablename__ = 'draft_catalogs'
    dataset_id: Mapped[str] = mapped_column(ForeignKey('dataset_versions.id'))
    feature_id: Mapped[str] = mapped_column(String(100))
    pricing_id: Mapped[str] = mapped_column(String(100))
    graph_id: Mapped[str] = mapped_column(String(100))
    rules_id: Mapped[str] = mapped_column(ForeignKey('rules_versions.id'))
    scoring_id: Mapped[str] = mapped_column(ForeignKey('scoring_versions.id'))
    __table_args__ = (
        ForeignKeyConstraint(['feature_id','dataset_id'],['feature_versions.id','feature_versions.dataset_id']),
        ForeignKeyConstraint(['pricing_id','feature_id'],['pricing_versions.id','pricing_versions.feature_id']),
        ForeignKeyConstraint(['graph_id','dataset_id'],['graph_versions.id','graph_versions.dataset_id']),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'",name='hash'))

class CatalogActivation(Base):
    __tablename__ = 'catalog_activations'
    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
    catalog_id: Mapped[str] = mapped_column(ForeignKey('draft_catalogs.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())

class DraftRuntime(Base):
    __tablename__ = 'draft_runtime'
    draft_id: Mapped[UUID] = mapped_column(ForeignKey('drafts.id'),primary_key=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey('guest_sessions.id'))
    catalog_id: Mapped[str] = mapped_column(ForeignKey('draft_catalogs.id'))
    creation_request_id: Mapped[UUID] = mapped_column(Uuid)
    creation_body_hash: Mapped[str] = mapped_column(String(64))
    creation_response: Mapped[dict] = mapped_column(JSONB)
    current_offer_id: Mapped[UUID | None] = mapped_column(Uuid)
    recast_cache: Mapped[dict] = mapped_column(JSONB,default=dict)
    __table_args__ = (UniqueConstraint('session_id','creation_request_id',name='uq_draft_creation_request'),
        ForeignKeyConstraint(['current_offer_id','draft_id'],['offers.id','offers.draft_id'],name='fk_runtime_current_offer'),
        CheckConstraint("creation_body_hash ~ '^[0-9a-f]{64}$'",name='hash'))

class SimulationAttempt(Base):
    __tablename__='simulation_attempts'
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    draft_id: Mapped[UUID] = mapped_column(Uuid)
    input_hash: Mapped[str] = mapped_column(String(64))
    attempt_number: Mapped[int] = mapped_column(Integer)
    command: Mapped[str] = mapped_column(String(24))
    request_id: Mapped[UUID] = mapped_column(Uuid)
    revision: Mapped[int] = mapped_column(Integer)
    simulation_version: Mapped[str] = mapped_column(String(100))
    engine_manifest_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    error_code: Mapped[str | None] = mapped_column(String(80))
    output_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(
        ForeignKeyConstraint(['draft_id','input_hash'],['draft_snapshots.draft_id','draft_snapshots.input_hash']),
        UniqueConstraint('draft_id','attempt_number',name='uq_simulation_attempt_number'),
        UniqueConstraint('draft_id','command','request_id',name='uq_simulation_attempt_request'),
        UniqueConstraint('draft_id','revision',name='uq_simulation_attempt_revision'),
        allowed('command',['release','retry_simulation'],'command'),allowed('status',['succeeded','failed'],'status'),
        CheckConstraint('attempt_number > 0 AND revision > 0',name='counters'),
        CheckConstraint("engine_manifest_hash ~ '^[0-9a-f]{64}$'",name='manifest_hash'),
        CheckConstraint("(status='succeeded' AND error_code IS NULL AND output_hash IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$') OR (status='failed' AND error_code IS NOT NULL AND error_code='engine_error' AND output_hash IS NULL)",name='outcome'))

# Phase 10 keeps historical guest ownership keys; immutable claims map them to accounts.
class Account(Base):
    __tablename__='accounts'
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    username: Mapped[str] = mapped_column(String(32),unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    primary_guest_id: Mapped[UUID] = mapped_column(ForeignKey('guest_sessions.id'),unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(CheckConstraint("username ~ '^[a-z0-9_]{3,32}$'",name='username'),)

class AccountSession(Base):
    __tablename__='account_sessions'
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey('accounts.id'),index=True)
    token_hash: Mapped[str] = mapped_column(String(64),unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__=(CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'",name='hash'),CheckConstraint('expires_at > created_at',name='expiry'))

class AccountOwnership(Base):
    __tablename__='account_ownership'
    guest_session_id: Mapped[UUID] = mapped_column(ForeignKey('guest_sessions.id'),primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey('accounts.id'),index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())

class AuthThrottle(Base):
    __tablename__='auth_throttles'
    bucket: Mapped[str] = mapped_column(String(80),primary_key=True)
    events: Mapped[list] = mapped_column(JSONB,default=list)

class DailyChallenge(Base):
    __tablename__='daily_challenges'
    id: Mapped[str] = mapped_column(String(80),primary_key=True)
    catalog_id: Mapped[str] = mapped_column(ForeignKey('draft_catalogs.id'))
    genre_id: Mapped[str] = mapped_column(ForeignKey('genres.id'))
    tier: Mapped[str] = mapped_column(String(16))
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(80))
    configuration: Mapped[dict] = mapped_column(JSONB)
    config_hash: Mapped[str] = mapped_column(String(64))
    seed: Mapped[str] = mapped_column(String(64))
    seed_commitment: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(CheckConstraint('closes_at > opens_at',name='window'),allowed('tier',['indie','studio','blockbuster'],'tier'),CheckConstraint("config_hash ~ '^[0-9a-f]{64}$' AND seed ~ '^[0-9a-f]{64}$' AND seed_commitment ~ '^[0-9a-f]{64}$'",name='hashes'),Index('ix_daily_challenges_opens_at','opens_at','id'))

class ChallengeAttempt(Base):
    __tablename__='challenge_attempts'
    draft_id: Mapped[UUID] = mapped_column(ForeignKey('drafts.id'),primary_key=True)
    challenge_id: Mapped[str] = mapped_column(ForeignKey('daily_challenges.id'))
    account_id: Mapped[UUID] = mapped_column(ForeignKey('accounts.id'))
    request_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(UniqueConstraint('challenge_id','account_id',name='uq_challenge_account_attempt'),UniqueConstraint('account_id','request_id',name='uq_challenge_creation_request'),UniqueConstraint('draft_id','challenge_id','account_id',name='uq_challenge_attempt_identity'))

class ChallengeSubmission(Base):
    __tablename__='challenge_submissions'
    draft_id: Mapped[UUID] = mapped_column(ForeignKey('results.draft_id'),primary_key=True)
    challenge_id: Mapped[str] = mapped_column(ForeignKey('daily_challenges.id'))
    account_id: Mapped[UUID] = mapped_column(ForeignKey('accounts.id'))
    output_hash: Mapped[str] = mapped_column(String(64))
    studio_score: Mapped[int] = mapped_column(Integer)
    profit_usd: Mapped[int] = mapped_column(BigInteger)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(ForeignKeyConstraint(['draft_id','challenge_id','account_id'],['challenge_attempts.draft_id','challenge_attempts.challenge_id','challenge_attempts.account_id']),UniqueConstraint('challenge_id','account_id',name='uq_challenge_submission'),CheckConstraint('studio_score BETWEEN 0 AND 100',name='score'),CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'",name='hash'),Index('ix_challenge_ranking','challenge_id','studio_score','profit_usd','submitted_at'))

class WhatIfAnalysis(Base):
    __tablename__='whatif_analyses'
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True)
    draft_id: Mapped[UUID] = mapped_column(ForeignKey('results.draft_id'))
    source_input_hash: Mapped[str] = mapped_column(String(64))
    source_output_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(40))
    slot: Mapped[str] = mapped_column(String(32))
    person_id: Mapped[UUID] = mapped_column(ForeignKey('people.id'))
    input_hash: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSONB)
    output_hash: Mapped[str] = mapped_column(String(64))
    outputs: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(ForeignKeyConstraint(['draft_id','source_input_hash'],['draft_snapshots.draft_id','draft_snapshots.input_hash']),
        UniqueConstraint('draft_id','version','slot','person_id',name='uq_whatif_variant'),UniqueConstraint('id','draft_id',name='uq_whatif_identity'),
        allowed('slot',[s.value for s in Slot],'slot'),CheckConstraint("input_hash ~ '^[0-9a-f]{64}$' AND output_hash ~ '^[0-9a-f]{64}$' AND source_output_hash ~ '^[0-9a-f]{64}$'",name='hashes'),Index('ix_whatif_history','draft_id','created_at','id'))

class WhatIfReceipt(Base):
    __tablename__='whatif_receipts'
    draft_id: Mapped[UUID] = mapped_column(Uuid,primary_key=True)
    request_id: Mapped[UUID] = mapped_column(Uuid,primary_key=True)
    analysis_id: Mapped[UUID] = mapped_column(Uuid)
    body_hash: Mapped[str] = mapped_column(String(64))
    request_body: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(ForeignKeyConstraint(['analysis_id','draft_id'],['whatif_analyses.id','whatif_analyses.draft_id']),CheckConstraint("body_hash ~ '^[0-9a-f]{64}$'",name='hash'))

class DraftReplay(Base):
    __tablename__='draft_replays'
    source_id: Mapped[UUID]=mapped_column(ForeignKey('drafts.id'),primary_key=True)
    request_id: Mapped[UUID]=mapped_column(Uuid,primary_key=True)
    child_id: Mapped[UUID]=mapped_column(ForeignKey('drafts.id'),unique=True)
    __table_args__=(CheckConstraint('source_id <> child_id',name='distinct_drafts'),)

class DraftRoom(Base):
    __tablename__ = 'draft_rooms'
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    draft_id: Mapped[UUID] = mapped_column(ForeignKey('drafts.id'), unique=True)
    host_id: Mapped[UUID] = mapped_column(ForeignKey('guest_sessions.id'))
    guest_id: Mapped[UUID | None] = mapped_column(ForeignKey('guest_sessions.id'))
    invite_hash: Mapped[str] = mapped_column(String(64))
    creation_request_id: Mapped[UUID] = mapped_column(Uuid)
    creation_hash: Mapped[str] = mapped_column(String(64))
    creation_response: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(16), default='waiting')
    revision: Mapped[int] = mapped_column(Integer, default=0)
    turn_seconds: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    events: Mapped[list] = mapped_column(JSONB, default=list)
    __table_args__ = (
        UniqueConstraint('host_id', 'creation_request_id', name='uq_room_creation'),
        CheckConstraint('guest_id IS NULL OR guest_id <> host_id', name='different_seats'),
        CheckConstraint('revision >= 0 AND turn_seconds BETWEEN 30 AND 180', name='bounds'),
        allowed('state', ['waiting', 'active', 'complete', 'cancelled'], 'state'),
        CheckConstraint("(state = 'active') = (deadline IS NOT NULL)", name='deadline'),
        CheckConstraint("state <> 'active' OR guest_id IS NOT NULL", name='two_players'),
        CheckConstraint("invite_hash ~ '^[0-9a-f]{64}$' AND creation_hash ~ '^[0-9a-f]{64}$'", name='hashes'),
        Index('ix_room_deadlines', 'state', 'deadline'))

class RoomReceipt(Base):
    __tablename__ = 'room_receipts'
    room_id: Mapped[UUID] = mapped_column(ForeignKey('draft_rooms.id'), primary_key=True)
    request_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('guest_sessions.id'))
    body_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (CheckConstraint("body_hash ~ '^[0-9a-f]{64}$'", name='hash'),)
