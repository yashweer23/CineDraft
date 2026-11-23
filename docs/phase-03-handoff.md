# Phase 3 — Next implementation prompt

Use after validating the Phase 2 stack locally. This file is a future handoff, not a claim that Phase 3 is implemented.

```text
Continue CineDraft with Phase 3 only: database domain design and API contracts.

First inspect README.md, docs/phase-02/summary.md, docs/phase-02/verification.md and all Phase 1 specifications. Preserve the original prototype and the Phase 2 frontend/backend health flow. Run the existing checks and resolve any configuration or real-PostgreSQL startup issue before changing the schema.

Design and implement SQLAlchemy models plus Alembic migrations for normalized people, movies, genres and role-specific credits; immutable dataset/feature/pricing/scoring versions; drafts, offers, picks, action records and results. Use one stable person identity across multiple professions, person-level duplicate constraints, integer USD and explicit slot identifiers. Store frozen input references and enough action/seed/version information for reproducibility. Keep fees and game-derived attributes distinguishable from source movie data.

Define typed request/response schemas and documented API contracts for the future catalog, draft actions and results. Map legal states, stale revisions, idempotency keys and ownership requirements from the Phase 1 documents. Implement only Phase 3 persistence/contracts and small repository round-trip checks; do not claim a complete authoritative game engine.

Add migrations, foreign keys, appropriate indexes and meaningful uniqueness constraints. Use explicit synthetic fixtures with no invented TMDB IDs or real movie credits. Verify schema creation and migration upgrade on a clean PostgreSQL database, and store/reload representative multi-role credits and draft snapshots.

Do not implement TMDB ingestion yet (Phase 4), data-derived ratings (5), collaboration graph (6), complete draft engine (7), or release simulator (8). Keep existing health routes and frontend checks working.

Update the README, ER diagram, schema notes and API contract documentation. Report exactly what was implemented and tested, the commands I should run in VS Code, and any remaining verification gate. Stop after Phase 3.
```
