# Phase 5 verification

## Integrated fixes — 23 October 2026

The revised package integrates the user-described host port mappings, setup and stack-check behavior, test-image contract files and writable cache, PostgreSQL test savepoint, and Alembic path separator. The root README documents the user's private environment settings; private `.env` files are preserved locally and excluded from the archive.

| Check on the revised package | Result in packaging environment |
|---|---|
| Backend unit suite | **114 passed**, 22 integration cases deselected |
| Original-game suite | **4 passed** |
| Frontend suite | **7 passed** |
| TypeScript and production build | Passed |
| Focused setup / connection-check smoke cases | **26 passed**: defaults, configured ports, preservation, invalid-port rejection and address precedence; health responses mocked |
| Docker image rebuild and real PostgreSQL tests | Not run here: Docker and PostgreSQL executables unavailable |
| Live TMDB requests and browser visual inspection | Not run for this update |

### User-reported local verification

The user reported **114 backend unit tests, 22 PostgreSQL integration tests, 4 original-game tests and the frontend → API → database connection check passing**, after rebuilding API/test images and recreating affected containers. Their working Windows addresses are studio `localhost:5174`, API docs `localhost:8001/api/docs`, PostgreSQL `127.0.0.1:5433`, and original game `localhost:5500`. These are the user's results on their local fixes; the packaging environment did not independently rerun the PostgreSQL suite.

The revised fixture opens a connection savepoint after schema creation and migration. Sessions bound to that connection can use their own savepoints, keeping service rollback from undoing the outer schema setup. Teardown asserts the outer transaction is active and the expected schema is still current, then rolls back the outer transaction to remove temporary data and schema. Run the 22 real database tests again after applying the package.

Current setup and all verification commands are in the root [README](../../README.md), including the separate unit and integration commands. The original report below is retained as historical evidence.

## Original package checks — 22 October 2026

| Check | Result in delivery environment |
|---|---|
| Backend tests | **114 passed, 22 skipped** |
| Frontend tests | **7 passed** |
| TypeScript and production build | Passed |
| Database-free calibration example | Executed; output bundled in data/phase5-calibration.json |
| Build CLI help | Passed |
| Current OpenAPI export | Generated and checked against the live application schema |
| PostgreSQL/Docker execution | Unavailable; integration tests skipped |
| Live TMDB requests | Not run; Phase 5 computation does not require them |
| Browser visual check | Attempted but unavailable: Playwright has no installed Chromium executable |

The backend suite adds 30 calculation cases and two API-contract/validation checks to the earlier 82 passing tests. They cover low-vote shrinkage, missing evidence, exact role separation, duplicate jobs, genre priors, popularity ties/missing values, role-specific percentiles, stable top-five ordering, integer fee bounds/rounding, coverage thresholds and deterministic reordered inputs.

Five new real-PostgreSQL tests join the previous 17. They test atomic publication/idempotency, dry-run, rollback after a forced price insert failure, immutable history/version conflicts, and actual talent routes with role-specific films and missing ratings. They were **not executed here**. Their presence is not evidence that real database behavior passed. Synthetic inputs are used throughout; no fabricated source records are imported into TMDB datasets.

The frontend suite adds empty-catalog handling, card/null/coverage displays, role and genre selection, and error recovery to the preserved health checks. Component tests and a successful build do not replace browser or end-to-end database verification. Inspect Talent Lab on desktop and mobile locally, including all five titles, missing artwork, evidence links and the external TMDB logo.

## Run the remaining local checks

```powershell
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose --profile verification run --rm --build api-tests
```

Expect migration `0002_phase4`, and **22 integration tests passed** with unrelated cases deselected. Then preview/build a sealed dataset, load Talent Lab, inspect cards/details, rerun the same build, and verify an older version remains unchanged. Record your actual results in the development log.

Dependencies are unchanged from Phase 4; existing installed locked dependencies were reused for checks. Python 3.12 and Node 24 are the tested runtime families. Historical migrations and original gameplay assets are checked byte-for-byte against the delivered Phase 4 ZIP. No claims from earlier verification reports are upgraded from skipped to passed.

## Known limitations

The first fee curve is the documented design baseline and can produce a pool too expensive for Indie budgets. Coverage is bounded by imported movies, and genre priors can be based on a small sample. The optimistic cost bound permits cross-role identity overlap and never enables a tier. Exact unique-person assignment, offer generation, action authorization and gameplay balance remain Phase 7. No benchmark against real hiring fees or individual artistic skill is claimed.
