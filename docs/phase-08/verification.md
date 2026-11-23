# Phase 8 verification — 27 October 2026

## Observed checks

| Check | Observed result |
|---|---|
| Backend units | 258 cases passed across the full run and final targeted simulation rerun |
| Frontend components | 30 passed, including release rendering, retries, evidence orientation and half-up decimal display |
| Frontend build | TypeScript and Vite passed |
| Original game | 4 cases passed, including the 540-draft invariant exercise |
| Migration syntax | Alembic `base:head` generated; 115 SQL statements and 18 PL/pgSQL functions parsed successfully |
| Model inventory | 32 tables; new `simulation_attempts` table |
| Pure example | Studio score 66; gross $20,008,096; profit $1,904,048; weekly totals reconcile |
| Random replay | Golden SHA-256 mapping, independent named draws, identical snapshots and changed surrounding Decimal precision tested |

Runtime: Python 3.12.14 and Node 24.22.1. Runtime dependency pins are unchanged. `pglast` was used only for packaging-time SQL parsing; it is not a new application dependency.

Arithmetic coverage includes manual expected score/finance values, half-up ties, full-precision reviews feeding gross, missing versus zero popularity, neutral/capped chemistry, exact evidence counts/identities, malformed numeric values, unsupported snapshots, score bounds, negative profit, short weekly totals and residual allocation. Twenty-five seeded high-score releases test bounded outcomes and reconciliation.

API units verify authentication, extra-field rejection, private result behavior, sanitized SQL failures, current version/schema and safe retry messages. The UI tests check a single successful result, no reroll button, explicit confirmed-failure retry, exact uncertain-request replay, stale server state, read-only report refresh and correctly oriented source jobs.

## PostgreSQL remains a local gate

**64 integration cases were skipped, not passed.** No usable PostgreSQL runtime or configured `TEST_DATABASE_URL` was available here. The suite includes the prior 52 cases and 12 new release/concurrency cases. There is no claim that migration execution, metadata drift, PostgreSQL triggers or row locks were verified at runtime during packaging.

From the project root with Docker's database running:

```powershell
docker compose --profile verification run --rm --build api-tests
```

Or from a configured backend virtual environment:

```powershell
python -m scripts.run_integration
```

The new real tests exercise full release/replay from a real finalized draft, deterministic retry after a recorded failure, other-owner denial, revoked sessions, stale/conflicting commands, invalid state, immutable attempts/results, protected downgrade, HTTP status/result responses and two simultaneous releases. Three fault-injection cases reject result, attempt or receipt writes and require complete transaction rollback.

Ordinary integration cases use per-test schemas inside outer rollback transactions, preserving the Phase 5 savepoint/isolation fix. Concurrent cases use separate connections to a committed temporary schema, then drop only their own generated `phase7_concurrency_<random>` schema; the existing fixture name is retained. A test DB role needs schema-creation rights. An abrupt process termination can leave that named test schema for inspection; normal application rows are never fixtures.

## Other limits

- No full live browser-to-database release journey, visual browser inspection or Windows execution was performed here. Component tests and a build do not replace those checks.
- No live TMDB fetch or new dataset publication was performed. Real-data breadth and genre coverage remain your catalog's responsibility.
- No production load, public deployment or strategic balance certification is claimed. The synchronous engine holds a draft lock while computing; normal API SQL timeout remains three seconds.
- Guest capability ownership is the existing local learning model, not an account recovery or production authentication system.
- Numerical repeatability does not establish predictive accuracy. Review, chemistry and revenue formulas are game assumptions with explicitly limited scope.

## Preservation and package checks

The original four game assets, migrations `0001_phase3` through `0004_phase7`, Phase 7 frozen input schema, frozen rules/scoring specification, dependency pins, Compose ports, environment examples, setup/check scripts and Docker test-image fixes remain unchanged. The persistence fixture's expected head advances to `0005_phase8` while keeping its savepoint and outer-schema assertions.

The cumulative ZIP has one `CineDraft-VSCode/` root, includes prior guides and a file checksum manifest, and excludes private environment files, credentials, dependencies, caches and build output. Documentation links, JSON syntax, preserved file bytes, ZIP integrity and manifest hashes are checked before delivery.
