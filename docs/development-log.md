# CineDraft development log

Use a new entry for each meaningful change. Record evidence you can explain in an interview.

## Entry template

**Date / phase:**

**Problem or goal:**

**Files I changed:**

**Design decision and reason:**

**What I ran locally:**

**Observed result:**

**Failure or limitation discovered:**

**What I learned:**

**Next small step:**

## Baseline

Phase 2: full-stack foundation implemented. See phase-02/verification.md for passing checks and the remaining local database/Docker/browser gates. Run those gates on your setup before Phase 3.

Phase 0: existing static game, preserved in this pack.

Phase 1: rulebook, scoring design, data specification, UX blueprint, state/edge-case specification and phase summary completed. New rule implementation remains future work. See verification.md for the measured baseline checks.


## Phase 3 — 21 October 2026

Added the domain schema, explicit Alembic migration, sealed data versions, proposed typed API contracts, synthetic persistence fixtures, isolated PostgreSQL integration suite and hands-on guide. Original gameplay source remains unchanged. Backend/frontend/offline SQL checks passed; real PostgreSQL and Docker execution remain local/CI verification gates. Next: Phase 4 TMDB ingestion. See docs/phase-03/verification.md.

## Phase 4 — 21 October 2026

Implemented the TMDB client, validated resumable checkpoints, exact credit/scope policy, manual film review, atomic sealed publication, read-only raw catalog routes and attribution. Added migration 0002 without changing 0001. Host API port is configurable. Backend: 82 passed, 17 PostgreSQL tests skipped; frontend: 4 passed/build passed; original prototype checks passed. Docker, real PostgreSQL execution and authenticated TMDB access remain local gates; no live token was supplied. Next: run those gates locally, collect/review/publish a small batch, then Phase 5 talent features, fictional prices and ranked works.

## Phase 5 — 22 October 2026

Implemented the Phase 1 talent/ranking/fee formulas with Decimal rounding, explicit sparse-data priors, exact role/movie deduplication and coverage diagnostics. Added atomic feature/pricing publication, deterministic manifests, four live talent API routes and a read-only Talent Lab. Migrations 0001/0002 and the original gameplay assets remain unchanged. Added a database-free synthetic calibration example; the initial curve can be too expensive for Indie and does not enable gameplay. Checks: 114 backend passed, 22 PostgreSQL skipped; 7 frontend passed; build passed. Browser visual verification was attempted but Chromium is not installed. Docker/PostgreSQL execution remains local. Next: run local checks, build your sealed dataset, inspect evidence, then Phase 6 collaboration graph.

## 25 October 2026 — Phase 7

Added owner-scoped server drafting, compatible catalog activation, exact distinct-person minimum assignment, saved deterministic offers, transactional/idempotent picks and rerolls, cached recast preview/cancel/confirm, abandonment and immutable final input snapshots. Added migration 0004, a memory-only guest-token inspector and hands-on/API recovery instructions. Preserved ports, setup/test fixes, previous migrations and original assets. Observed 200 backend unit passes, 52 PostgreSQL skips, 22 frontend passes, 4 original-game passes, frontend build and static migration SQL/function syntax checks. Real database execution and browser journeys remain local verification gates. Phase 8 is scoring and release simulation.

## 27 October 2026 — Phase 8

Executed the frozen baseline scoring/release specification using Decimal arithmetic and independent SHA-256 streams. Added one immutable result per released draft, safe failed-attempt recording and retry, owner-only result/status reads, migration 0005, a Release Report and a read-only saved-result replay command. Preserved version pins, earlier snapshots/migrations, ports and original gameplay assets. Observed 258 backend unit passes across suite/final targeted checks, 64 PostgreSQL skips, 30 frontend passes, 4 legacy passes, a successful frontend build and static migration syntax checks. Database runtime and browser journeys remain local gates. Next: Phase 9's full drafting/results interface.

## 28 October 2026 — Phase 9

Added the guided brief/draft/review/recast/premiere/report studio, memory-only token recovery, exact uncertain-command replay with current-state reconciliation, saved-offer named rosters, candidate dossiers, native dialogs and responsive layouts. Kept earlier inspectors under developer tools. Added one owner-only GET roster route with no new migration or changes to frozen rules/results. Verified 262 backend units, 39 frontend components, four legacy checks, the production build and two Chromium journeys with mock HTTP. All 66 real PostgreSQL cases and the live browser/database journey remain local verification gates.

## 1 November 2026 — Phase 10

Implemented accounts and guest claims, version-pinned daily challenges, one-attempt/deadline enforcement, automatic official submissions, result/seed embargo and ranked reads after close. Extended the guided studio with account controls, challenge entry/resume and leaderboards. Added migration 0006 (39 tables), a Windows timezone fallback, contracts, operator CLIs and hands-on recovery instructions. Frozen engine arithmetic and historic gameplay records stay unchanged. Exact observed checks and unrun database gates are recorded in [Phase 10 verification](phase-10/verification.md). Next: controlled what-if comparisons, separate from official results.
