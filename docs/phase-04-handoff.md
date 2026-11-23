# Phase 4 — TMDB ingestion handoff

Continue only with Phase 4 after the Phase 3 migration and real PostgreSQL tests pass locally or in CI. Preserve the original playable prototype, studio health flow and versioned database history.

Inspect README.md, all Phase 1 specifications, docs/phase-03/database-design.md, api-contracts.md and verification.md, plus the actual models/migration/contracts. Do not claim previous database tests passed unless there is a real PostgreSQL result.

## Implement

1. A backend-only TMDB client with environment-based credentials, explicit timeouts, bounded retries/backoff, pagination and rate-limit handling. Never expose secrets in VITE variables, logs, ZIPs or git. Inspect current official TMDB documentation and attribution requirements when implementing.
2. An explicit CLI ingestion workflow, small configurable batches and resumable checkpoints outside immutable published tables. Do not fetch TMDB for each gameplay action.
3. Stable provider person/movie identity, released English narrative-feature filtering, a queue/report for unknown runtime or ambiguous exclusions, original credits and provenance. Exclude documentaries, stand-up/concerts, archival/self-only appearances and unreleased titles under the Phase 1 policy; do not infer exclusions from a genre alone.
4. Exact versioned role-job mapping: Director; acting cast; Writer/Screenplay; Director of Photography; Original Music Composer. No known-for shortcut. Keep one person identity across roles, and keep Reznor and Ross as separate verified identities.
5. Source-credit/composite deduplication, nullable missing fields, validated source IDs and real image configuration. Do not fabricate source credits, popularity, ratings or artwork.
6. Validate and publish new immutable dataset versions atomically. The model's content_hash hashes its configuration/manifest; include actual export checksums in that manifest. Preserve old dataset versions and frozen games. New source observations go into a new dataset, never sealed-row updates.
7. Coverage and exclusion reports, role/genre counts, duplicate detection and explicit source attribution. Expose only implemented read-only catalog data appropriate to this phase; do not pretend uncomputed ratings/prices/ranked top-five lists exist. Revise/export contracts explicitly if adding raw catalog routes.
8. Unit tests using clearly marked recorded/synthetic responses, integration checks against PostgreSQL, and an opt-in small live API smoke check that requires a local key. Report exactly which checks ran.

## Do not advance scope

Phase 5 computes ratings, notable-work ranking and fictional prices. Phase 6 builds the collaboration graph. Phase 7 implements authoritative actions, exact assignment feasibility, owner/guest authorization and complete idempotency (including owner-scoped create requests). Phase 8 implements simulation jobs and results. Phase 9 completes the game UI.

Deliver a cumulative VS Code ZIP, updated setup/ingestion guide, API-key configuration example without secrets, verification report and Phase 5 handoff. Do not publish a hosted site. Stop after Phase 4.
