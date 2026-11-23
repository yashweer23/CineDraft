# Phase 8 — scoring and release simulation

Continue the cumulative VS Code ZIP workflow. Implement Phase 8 only; do not deploy a site. Preserve private environment files, ports 5433/8001/5174, original assets, old migrations, sealed data and draft history. Phase 7 migration head is `0004_phase7` with 31 tables.

## First read and verify

Read the Phase 1 scoring/game rules, Phase 5 feature/fee formulas, Phase 6 graph rules, Phase 7 design/API/verification and `backend/app/drafting/rules.py`. Run the full real PostgreSQL suite before claiming persistence/locking gates passed: the Phase 7 packaging run observed 200 unit passes and 52 PostgreSQL skips, not database success. Frontend had 22 passing cases and the original game 4.

## Implement

1. Execute the frozen `scoring:baseline-1.0` / `simulation-1.0` contract for finalized `phase7-v1` inputs. Preserve historical `phase3-v1` synthetic snapshots and results. Never re-price or replace selected people or source versions during simulation.
2. Compute weighted genre/talent aggregates, four-actor popularity (missing uses 50), efficiency, exactly twelve chemistry edges and deterministic studio score. Use the frozen selected role features and collaboration evidence; do not fetch current TMDB data or sum all graph edges.
3. Implement named deterministic random streams for critics, audience and revenue. Record algorithm version and draw mapping; never reuse mutable offer randomness. Specify exact Decimal precision and rounding. If the existing reserved version cannot be implemented as specified, add an explicit compatible version strategy without rewriting old finalized inputs.
4. Produce reviews, committed production cost, marketing, gross, studio receipts, all-in profit, return and four weekly totals according to the frozen formulas. No money is earned or spent outside fictional game state. Preserve full precision for downstream review formulas and named integer-dollar rounding for financial outputs.
5. Add owner-authorized idempotent release/result/retry flows following existing domain states. Prevent double simulation/result rows, preserve failed execution state safely and retain immutable input/output hashes. Recovery and concurrency must be tested with real PostgreSQL.
6. Add a small result inspector to the existing studio. Explain weighted score contributions and financial reconciliation, with source-backed chemistry and clear synthetic/fictional labels. The polished game UI remains Phase 9.
7. Add deterministic, rounding, boundary, accounting, replay, rollback and concurrent-release tests. Run native/component/build checks and the actual PostgreSQL suite. Keep any unrun gate explicit.
8. Regenerate current OpenAPI/new result schemas, document setup and hands-on examples, package a cumulative ZIP plus standalone README, and write the Phase 9 handoff.

## Phase 7 boundaries to preserve

- Capabilities are 30-day guest tokens, hashed in the DB and memory-only in the browser. Revocation/expiry blocks access without deleting history. Do not weaken ownership for result routes.
- Mutation receipts replay their original response before stale-revision validation. The inspector retries uncertain writes with the exact saved body and request ID.
- Current-offer pointers and recast caches are separate from immutable offers. Cached preview IDs survive cancellation. Recast refund, replacement and receipt are atomic.
- The finalized snapshot embeds a null snapshot hash to avoid circular hashing; its enclosing row and live draft response carry the hash.
- Catalog activation affects new drafts only. No fixture namespace may be presented as real movie data.
