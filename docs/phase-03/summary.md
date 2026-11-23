# Phase 3 — Database and contracts

Implemented on 21 October 2026 for the local CineDraft project.

- 21 SQLAlchemy tables covering stable identities, dataset-scoped movie/person fields, genres, original/normalized credits, derived role features/prices, versioned rules/scoring, drafts, offers, candidates, picks, actions, final input snapshots and results.
- Explicit Alembic revision `0001_phase3`: tables, composite foreign keys, indexes, checks and 25 triggers backed by eight PostgreSQL functions.
- One-way sealed versions and offers; append-only source/derived rows; sealed dependency requirements; frozen draft versions/seed; immutable final inputs/results.
- Integer-dollar allocation and spending constraints, person-level roster uniqueness and offer/price linkage.
- Strict Pydantic requests and responses; proposed OpenAPI/JSON Schema exports; no prematurely exposed game endpoints.
- Canonical snapshot/result hashes and small persistence/replay helpers.
- An opt-in, repeatable synthetic fixture and snapshot inspection command. The fixture uses eight fictional people and one fictional film, with a multi-role director/writer identity, handwritten fees and a marked synthetic result.
- Real PostgreSQL migration/round-trip/constraint integration tests, isolated in temporary schemas; an optional Compose verification image; existing GitHub CI enables the database suite.
- Windows setup/update instructions, ER diagrams, transaction/ownership semantics, SQL exercises and Phase 4 handoff.

Preserved: original four playable assets, root prototype command, React health flow, backend health endpoints and all prior design documents. The studio/version labels now say Phase 3.

Not implemented in this phase: TMDB requests, data-derived ratings/pricing, top-five ranking computation, collaboration graph, full state/authorization/idempotency engine, job orchestration, actual simulation, accounts or new playable game UI. These are intentionally assigned to later phases.

Verification limits are in [verification.md](verification.md). In particular, the delivery environment cannot execute PostgreSQL or Docker; local/CI checks are required before calling the live database migration verified. Phase 2's local Docker engine issue must also be resolved on the user's machine.
