# CineDraft — Phase 4 VS Code project

Phase 4 implements **TMDB ingestion and a read-only catalog API**. Import a small batch, inspect the coverage report, and publish an immutable dataset. This cumulative ZIP includes the original game, React studio, FastAPI backend, database migrations, tests and every earlier phase document.

The importer is ready for your local TMDB token. No live TMDB data or credentials are bundled. Ratings for talent, fictional prices and ranked top-five works are Phase 5; authoritative game actions are Phase 7; simulation is Phase 8.

## Start here

Open the extracted `CineDraft-VSCode` folder in VS Code. Keep your existing root `.env`, `backend/.env`, `frontend/.env` and PostgreSQL volume when upgrading. Back up your own source edits before replacing files. Do not reset the database password or delete the volume.

Use Node 24.15+ in the 24.x line. Start Docker Desktop and wait for its Linux engine. In a terminal at the project root:

```powershell
node scripts/setup-env.cjs
docker info
```

The generator preserves existing environment files. Add this line to **backend/.env**, with your own TMDB **API Read Access Token** from your account's API settings:

```dotenv
TMDB_READ_ACCESS_TOKEN=your_token_here
```

Keep the token local. Use the long Read Access Token, not the API Key string. The API and synthetic tests work without a TMDB token; importing requires one.

If you use a different API port, retain it by setting `API_PORT` in the root `.env`, for example `API_PORT=8001`. This changes the host port; Compose services still communicate internally on port 8000.

```powershell
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose --profile verification run --rm --build api-tests
```

Expected migration: `0002_phase4 (head)`. The last command runs 17 tests against real PostgreSQL in isolated temporary schemas. Run these before importing on your setup. A green health check only verifies connectivity, not migrations.

## First hands-on import

```powershell
docker compose run --rm api python -m scripts.import_tmdb smoke
docker compose run --rm api python -m scripts.import_tmdb start --dataset first-import-v1 --pages 1 --max-movies 20
```

Save the `run_id` printed by `start`. In PowerShell, replace the placeholder once:

```powershell
$runId = 'paste-the-printed-run-id-here'
docker compose run --rm api python -m scripts.import_tmdb status --run $runId
docker compose run --rm api python -m scripts.import_tmdb review --run $runId
docker compose run --rm api python -m scripts.import_tmdb publish --run $runId
```

`start` downloads and checkpoints; `review` explains inclusion, exclusions and coverage; `publish` makes the version visible to the catalog. Read the report before publishing. If collection stops, run `resume --run $runId`. At least one eligible film is required to publish. Review/excluded films remain labeled and are hidden by the default movie listing.

Open the [studio](http://localhost:5173), [original game](http://localhost:5500), and [API docs](http://localhost:8000/api/docs). Substitute your `API_PORT` in the last URL, or open **API documentation** from the studio. In Swagger, try `GET /api/catalog/datasets`, then use `tmdb:first-import-v1` for the movie/people endpoints.

## Guides

- [Setup and troubleshooting](docs/phase-04/setup.md) — Windows, ports, Docker and native Python.
- [Ingestion and review policy](docs/phase-04/ingestion.md) — checkpoints, roles, exclusions and overrides.
- [Live catalog API](docs/phase-04/api.md) — endpoints and data limitations.
- [Hands-on exercises](docs/phase-04/hands-on.md) — trace a response, resume and compare versions.
- [What changed](docs/phase-04/summary.md) and [verification results](docs/phase-04/verification.md).
- [Phase 5 handoff](docs/phase-05-handoff.md), [complete roadmap](docs/CineDraft_Development_Roadmap.md).
- [Phase 3 README](README-phase3.md), [Phase 1 specifications](docs/phase-01/phase-01-summary.md).

Root `npm start` runs the original prototype only. The React studio remains a development dashboard; its design preview does not become playable from an import. Live catalog contracts are in `contracts/openapi.current.json`; future game contracts remain separate in `contracts/openapi.proposed.json`.

Delivery checks: 82 backend tests and 4 frontend tests passed; frontend build and original-game checks passed. The 17 real PostgreSQL tests, Docker execution and live TMDB smoke request remain local verification steps. See the report for exact scope.
