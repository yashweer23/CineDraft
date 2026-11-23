# Phase 7 verification — 25 October 2026

## Observed packaging results

| Check | Result |
|---|---|
| Backend full pytest collection | **200 passed, 52 skipped** |
| Exact matching | 40 seeded small catalogs compared with independent exhaustive assignments; multi-role collisions, equality and legality checks passed |
| API unit checks | Missing/malformed authorization, forbidden client fields, stale-error envelope, current OpenAPI and reserved simulation routes passed |
| Snapshot contract | Complete role snapshots and identity/role mismatch rejection passed; historical contract tests retained |
| Frontend component tests | **22 passed**, including 8 Draft Inspector cases |
| Frontend production build | TypeScript and Vite passed |
| Original game suite | **4 passed**, including its 540-draft engine exercise |
| Migration SQL syntax | Alembic `base:head` generated; **108 SQL statements and 16 PL/pgSQL functions** parsed successfully |
| Assignment example | Synthetic exact minimum $500K; affordable-but-impossible $100K writer blocked |

Python 3.12 and Node 24.19 were used. No new runtime dependency was added. The SQL parser was a packaging-only tool, not a project dependency.

## Required local checks

**The 52 real PostgreSQL cases did not run here.** No usable PostgreSQL/Docker runtime was available. Static syntax parsing does not execute triggers, verify Alembic metadata drift, exercise row locks or prove service transactions. Tests include 15 new Phase 7 integration/concurrency cases and all 37 prior cases.

Run from the project root with Docker's database available:

```powershell
docker compose --profile verification run --rm --build api-tests
```

Or, from a configured native backend virtual environment:

```powershell
python -m scripts.run_integration
```

This derives `TEST_DATABASE_URL` from `backend/.env` without printing its password. Ordinary tests create a unique schema inside an outer rollback transaction, retaining the Phase 5 savepoint fix. Concurrency tests need separate committed connections: they create one uniquely named `phase7_concurrency_<random>` schema per case, apply migrations there, and remove only that schema in cleanup. The DB test user therefore needs schema-creation permission. An abruptly killed concurrency run can leave that named test schema for manual inspection/cleanup; it does not touch normal application tables.

The suite checks new/old migration round trips and metadata drift, preserved historical snapshots, no cross-owner read/write, expired/revoked tokens, create/action idempotency, stale revisions/offers, invalid candidates, reroll limits, cached recasts, exact refunds, failure rollback, sealed input mismatches, immutable final snapshots, protected downgrade and concurrent requests. These are written checks, not observed runtime successes in this environment.

Your previously reported 22 passing Phase 5 database checks are historical evidence only; they do not certify this new migration.

## Other unverified gates

- No live browser-to-API-to-PostgreSQL draft journey, visual browser inspection or Windows execution was completed here. The inspector has component tests and a type-checked build.
- No live TMDB requests were made. Real catalog breadth, sparse-data behavior and playable-tier coverage depend on your imported data.
- Feasibility is exact, but latency and contention at the supported 5,000-profile limit have not been production load-tested. The API retains its three-second SQL timeout.
- Pricing fairness, per-genre choice coverage and strategic balance remain calibration work. Enabled means an affordable distinct-person completion exists.
- Guest capabilities are a local learning ownership model, not production account management. No renewal/recovery, rate limits or public deployment is included.
- The baseline scoring specification is frozen for future execution. No Phase 8 simulation, results or financial performance claims are made.

## Preservation and packaging

The four original game assets, first three migrations, Compose port settings, setup/check scripts, environment examples, Alembic path separator and Docker test-image fixes are preserved from the Phase 6 package. The persistence fixture keeps its savepoint and isolation assertions; only its expected migration head changes.

The cumulative ZIP has a single `CineDraft-VSCode/` root and a SHA-256 manifest. Credentials, private environment files, dependency folders, caches and build output are excluded. The README is also supplied separately. Before delivery, archive integrity, manifest hashes, local documentation links and required files are checked.
