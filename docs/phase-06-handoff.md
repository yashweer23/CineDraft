# Phase 6 — collaboration graph and evidence

Continue with Phase 6 only. Keep the cumulative VS Code ZIP workflow with code, docs and hands-on exercises. Preserve original gameplay assets, historical migrations, imported datasets, computed feature/pricing versions and old draft snapshots. Do not deploy a hosted site.

## Inspect first

Read the Phase 1 scoring/data specs, Phase 3 versioned schema, Phase 4 import scope and Phase 5 formulas/API/verification. On 23 October 2026 the user reported 114 backend unit tests, 22 PostgreSQL integration tests, 4 original-game tests and the frontend/API/database connection check passing locally after the startup and test-isolation fixes. This is user-reported local evidence; PostgreSQL was unavailable in the packaging environment. Rerun the real PostgreSQL suite for subsequent code changes. Phase 5 code and calibration output are implemented; the fee curve is not proven balanced. Preserve the configurable host ports (currently 5433/8001/5174), native environment mappings, test-image contracts/cache and savepoint isolation fixes.

## Implement

1. Build a versioned collaboration graph from a sealed dataset using distinct eligible shared movie IDs and exact professional-role pairs. Deduplicate multiple jobs on the same film. Keep multi-role identities consistent and prohibit self-pair edges.
2. Preserve movie and role evidence for every edge. A pair's shared acting credits must not imply they worked together as director/composer. No friendship or subjective relationship claims.
3. Implement the Phase 1 capped edge formula (`min(12, 4 × shared-film count)`) with explicit versioned configuration. Keep full evidence even when additional films no longer increase the bonus. Describe missing shared evidence as “No shared credits found in this dataset.”
4. Define a canonical ordering for person-role pairs and deterministic graph/content hashes. Use a new migration if new persistence is required; never edit migrations 0001 or 0002 after application.
5. Explicit offline build/preview commands, atomic publication, safe reruns and old-version preservation. Add implemented read-only API routes and update the current contract export.
6. An evidence view in the local studio showing actual shared films and credited jobs; maintain source attribution and missing-data handling. No invented graph edges or fake source films to fill empty states.
7. Meaningful tests for role direction, identity uniqueness, duplicate job collapse, bonus caps, missing credits, deterministic construction and database rollback/immutability. Add local/CI PostgreSQL commands and honest verification results.
8. Updated setup, hands-on graph exercises, summary and Phase 7 handoff in the next cumulative ZIP.

## Boundaries

The Phase 1 final chemistry score uses twelve specified drafted-role relationships. You may implement its pure evidence/math helper if needed for graph validation, but do not implement authoritative draft actions or simulations in this phase. Phase 7 handles exact assignment feasibility, ownership, idempotent transactional actions and price locking. Phase 8 simulates outcomes; Phase 9 completes the game UI. Imported absence is not proof that two people never collaborated outside this catalog.
