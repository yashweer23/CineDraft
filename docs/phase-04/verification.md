# Phase 4 verification — 21 October 2026

## Checks executed in the delivery environment

| Check | Observed result |
|---|---|
| Backend `python -m pytest -q` | **82 passed, 17 skipped** |
| Frontend tests | **4 passed** |
| Frontend production build | Passed TypeScript and Vite build |
| Original-game tests | **4 passed**, including 540 seeded draft runs |
| CLI argument help | Passed |
| Current/proposed contract generation | Generated from application definitions |
| Upgrade/downgrade offline SQL | Parsed with PostgreSQL syntax parser; ten PL/pgSQL functions parsed |
| Schema/model comparison | 23 table definitions and indexes match compiled metadata |
| Historical preservation | Migration 0001 and original four gameplay source assets match Phase 3 |

Backend tests include mocked bearer authentication, discovery parameters, bounded retries, 429/5xx handling, failure sanitization, invalid payload rejection, exact credits, eligibility/review policy, deduplication, safe image paths, and live route registration. Fixtures are explicitly synthetic and never masquerade as real TMDB records. No live movie requests were made.

The 17 skipped tests require a real PostgreSQL server: 13 existing persistence checks and 4 new ingestion/catalog checks. The new tests cover successful checkpoint reuse, idempotent publication, sealed resources, role-specific films, review-only publication refusal and atomic rollback for conflicting credits. Their presence is not a claim that they ran.

## Required checks on your machine

```powershell
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose --profile verification run --rm --build api-tests
docker compose run --rm api python -m scripts.import_tmdb smoke
```

Expected migration head is `0002_phase4`. The test service should report 17 passed (and unrelated tests deselected), with no integration skips. Then run a small import, inspect its report, publish and query the catalog as in the README. Record your actual results in the development log.

Docker/Compose execution and real PostgreSQL migrations/triggers were **not executed here**. Offline SQL parsing cannot establish runtime transaction behavior. The TMDB smoke/import was **not executed here** because no user token was provided. Browser rendering of the external TMDB logo was not verified; confirm it loads and meets current branding guidance locally. The remote image is referenced rather than bundled.

The tested Python runtime is 3.12.14 and Node runtime is 24.19.0. Existing dependency pins are retained; `httpx2==2.15.1` moved from development-only to runtime requirements for ingestion. No package versions were upgraded for this phase. The SQL parser used for offline verification is a tooling dependency and is not required by the app.

## Practical limits

The imported sample is bounded and selection-biased. Missing or ambiguous source metadata can leave movies under review. Person metadata uses a documented stable first-observation rule; it does not query full person careers. Per-credit manual overrides and checkpoint retention cleanup are not implemented. Published snapshots stay immutable. Ratings/prices, ranked top-five works, game write endpoints and simulations remain later phases.
