# CineDraft — Phase 5

**Talent ratings, fictional hiring prices, and ranked notable works.** This cumulative VS Code project includes the earlier phases and your startup, port, database-test and setup fixes. Updated 23 October 2026.

Phase 5 builds explainable role profiles from a sealed local dataset, publishes immutable feature/pricing versions, and displays them in the React **Talent Lab**. Builds do not call TMDB. The original playable game remains available separately; authoritative drafting is Phase 7.

If you downloaded this README separately, save it as `README.md` in your CineDraft project root so its documentation links resolve.

## 1. Keep your working files

Back up your edits before merging the updated ZIP into your project. Preserve root `.env`, `backend/.env`, `frontend/.env`, your database password and PostgreSQL volume. Private environment files are excluded from the ZIP. If extracting into a new folder, copy those three files to their matching locations before starting.

Open the folder containing `compose.yaml` in VS Code. Your project is currently at:

```text
C:\Users\saiya\OneDrive\Documents\Projects\cinedraft
```

Commands below use **PowerShell from the project root**, unless another folder is shown. Start Docker Desktop with Linux containers. For native commands and frontend checks, use **Node 24.15+ within the 24.x release line**; for a native backend use **Python 3.12**. There are no root npm dependencies to install: `npm ci` belongs in `frontend/`.

## 2. Confirm your ports

| Service | Address on Windows | Internal Docker address |
|---|---|---|
| Studio / Talent Lab | [http://localhost:5174](http://localhost:5174) | `web:5173` |
| API documentation | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | `api:8000` |
| PostgreSQL | `127.0.0.1:5433` | `db:5432` |
| Original game | [http://localhost:5500](http://localhost:5500) | `prototype:5500` |

Keep these lines in your existing **root `.env`**, alongside your existing database credentials:

```dotenv
POSTGRES_PORT=5433
API_PORT=8001
WEB_PORT=5174
```

In **`backend/.env`**, keep the database name, user and password aligned with the root file, and retain your TMDB token. Native database connections use:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5433
```

In **`frontend/.env`**, use:

```dotenv
API_PROXY_TARGET=http://127.0.0.1:8001
VITE_LEGACY_URL=http://127.0.0.1:5500
```

Leave Compose's API `DB_PORT` at `5432` and its frontend proxy at `http://api:8000`: these are container addresses. Host port `5174` avoids CyberSentinel on `5173`.

`node scripts/setup-env.cjs` creates missing files and preserves existing files. New defaults are `5432`, `8000` and `5173`. It validates all three root ports, uses the configured database/API ports when generating native files, and generates CORS origins for the configured web port. **Changing root `.env` later does not rewrite existing backend/frontend `.env` files.** Apply the blocks above manually if needed. For a fresh installation, run setup first, then adjust these three files to your chosen ports.

## 3. Rebuild and start

With the existing environment files checked:

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose ps
npm run check:stack
```

Expected migration head: **`0002_phase4`**. Phase 5 uses the feature and pricing tables introduced earlier and adds no migration. Rebuilding picks up copied CLI/test files; Compose recreates services whose configuration changed.

The connection check chooses `CINEDRAFT_WEB_URL` if set; otherwise it uses process `WEB_PORT`, then root `.env`, then `5173`. Your configuration checks port `5174`. Expected output:

```text
Frontend -> Vite proxy -> FastAPI: connected.
FastAPI -> PostgreSQL: SELECT 1 passed.
```

A one-off override is `$env:CINEDRAFT_WEB_URL = 'http://localhost:5174'`. Remove it afterward with `Remove-Item Env:CINEDRAFT_WEB_URL` so future checks follow root `.env` again.

## 4. Choose or import a dataset

Open the [API documentation](http://localhost:8001/api/docs) and execute **`GET /api/catalog/datasets`**. Copy an exact sealed dataset ID. If you already published a Phase 4 dataset, reuse it and go to step 5.

For a new TMDB import, this client expects the long **API Read Access Token** in `backend/.env`:

```dotenv
TMDB_READ_ACCESS_TOKEN=your_tmdb_read_access_token
```

The client uses bearer authentication; a short v3 API key is not a drop-in value for this variable. Keep the token out of frontend and `VITE_` settings. Run:

```powershell
docker compose run --rm api python -m scripts.import_tmdb smoke
docker compose run --rm api python -m scripts.import_tmdb start --dataset first-import-v1 --pages 1 --max-movies 20
```

Save the actual `run_id` printed by `start`, then substitute it below:

```powershell
$run = 'PASTE-THE-PRINTED-RUN-UUID'
docker compose run --rm api python -m scripts.import_tmdb review --run $run
```

Inspect the report and resolve blocking review issues using the [Phase 4 instructions](docs/phase-04/setup.md). When ready, publish:

```powershell
docker compose run --rm api python -m scripts.import_tmdb publish --run $run
```

If interrupted, resume with `docker compose run --rm api python -m scripts.import_tmdb resume --run $run`. Use a new dataset label if `first-import-v1` already exists. A staging import cannot supply ratings until published.

For practice without a token, seed the synthetic dataset instead:

```powershell
docker compose run --rm api python -m scripts.seed_demo
```

Use dataset ID `fixture:dataset-v1`. It contains one fictional movie and eight fictional people, so sparse coverage is expected. The UI labels synthetic records.

## 5. Preview and publish talent ratings

Set the exact dataset ID from step 4. For the synthetic option, replace it with `fixture:dataset-v1`:

```powershell
$dataset = 'tmdb:first-import-v1'
$version = 'first-ratings-v1'
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version $version --dry-run
```

Inspect role coverage, missing genres, fee ranges and budget diagnostics. A dry run calculates without publishing. Then publish:

```powershell
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version $version
```

This creates **`features:first-ratings-v1`** and **`pricing:first-ratings-v1`** together in one transaction. Repeating the exact build returns `created: false`. Changed source data or formulas require a new label; labels accept 1–71 lowercase letters, digits, underscores or hyphens. Sealed versions remain unchanged. No import or rating build runs at API startup.

Ratings are game estimates based on available evidence. Hiring fees are fictional USD amounts, not real salaries or quotes. Price diagnostics do not enable budget tiers or guarantee that every draft can be completed; exact draft feasibility belongs to Phase 7.

## 6. Explore Talent Lab

1. Open [http://localhost:5174](http://localhost:5174), scroll to **Talent Lab**, and click **Load talent catalog**.
2. Select the published version, professional role and genre. Use **Refresh talent catalog** after another build.
3. Inspect ratings, fictional fees, coverage warnings and up to five ranked works for that role.
4. Open **View calculation evidence** to inspect source contributions and pricing arithmetic.
5. Compare the same person across professional roles, inspect a low-coverage profile, then rerun the same build to confirm it is unchanged.

The API is implemented: Swagger includes talent version, profile, profile-detail and report routes alongside catalog and health routes. This phase provides research and ratings; the new studio's authoritative draft actions come later.

Continue with the [hands-on exercises](docs/phase-05/hands-on.md), [formulas](docs/phase-05/formulas.md) and [API guide](docs/phase-05/api.md).

## 7. Run verification

From the root, with Docker running:

```powershell
# Unit tests: the rebuilt image includes the contract files.
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"

# PostgreSQL tests: temporary schema and transaction per test.
docker compose --profile verification run --rm --build api-tests

# Original playable game.
npm test

# React tests and TypeScript / production build.
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend

# Running frontend -> API -> PostgreSQL.
npm run check:stack
```

Expected suite sizes: **114 backend unit tests**, **22 database integration tests**, **4 original-game tests** and **7 frontend tests**. The integration runner supplies the real database URL; ordinary pytest without it skips the integration cases. The test image now uses writable `/tmp/pytest-cache`.

**Your reported local verification:** 114 backend unit tests, 22 database integration tests and 4 original-game tests passed, along with the frontend → API → database check, after rebuilding API/test images and recreating affected containers. This records your supplied results, not a new Docker/PostgreSQL run here. The [verification record](docs/phase-05/verification.md) separates those results from checks performed on this revised package.

## 8. Optional native development in VS Code

Use Python and Vite in VS Code terminals while Docker supplies PostgreSQL. Stop the Docker API/frontend first to free ports `8001` and `5174`:

```powershell
docker compose stop api web
docker compose up -d db
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Confirm the native environment values in step 2. In a backend terminal:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8001
```

In another terminal at the project root:

```powershell
npm --prefix frontend run dev -- --port 5174
```

Native Vite needs that explicit port argument; it does not automatically use root `WEB_PORT`. Its proxy reads `frontend/.env`. Restart Vite after changing that file. In another root terminal, run `npm run check:stack`.

For native backend tests, use another terminal in `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
.\.venv\Scripts\python.exe -m scripts.run_integration
```

Native import/build commands use the same module arguments shown earlier, with `.\.venv\Scripts\python.exe` and no Docker prefix. A database-free arithmetic example is `.\.venv\Scripts\python.exe -m scripts.talent_example` from `backend/`; the output is also in `data/phase5-calibration.json`.

The original game can remain in its Docker container. To run it natively, stop that container with `docker compose stop prototype`, then run `npm start` from the root. To return to full Docker, stop native servers with Ctrl+C and run `docker compose up --build -d`.

On macOS/Linux, use `python3.12` and the corresponding `.venv/bin/python` paths.

## Integrated fixes

| File / setting | Integrated behavior |
|---|---|
| `compose.yaml` | DB host port maps to container `5432`; configurable web host port maps to container `5173`. |
| Your root `.env` | Preserve ports `5433`, `8001` and `WEB_PORT=5174`. |
| `.env.example` | Adds default `WEB_PORT=5173` and occupied-port guidance. |
| Your `backend/.env` | Native DB uses `DB_PORT=5433`. |
| Your `frontend/.env` | Native proxy targets `http://127.0.0.1:8001`. |
| `scripts/setup-env.cjs` | Includes/validates DB, API and web ports; generates the native proxy from `API_PORT`; preserves existing files. |
| `scripts/check-stack.cjs` | Uses configured `WEB_PORT`; retains the full-URL override. |
| `backend/Dockerfile.test` | Copies contracts to `/contracts` and uses a writable pytest cache. |
| `backend/tests/test_persistence.py` | Adds a savepoint after migration; asserts the outer transaction and temporary schema survive each test. |
| `backend/alembic.ini` | Adds `path_separator = os`. |
| `README.md` | Documents your addresses, setup, verification and native development commands. |

## Troubleshooting

| Problem | Action |
|---|---|
| Studio port occupied | Keep `WEB_PORT=5174`; recreate Docker web, or pass `--port 5174` to native Vite. |
| Native frontend cannot reach API | Confirm proxy target `8001`, restart Vite and check that the API is running. |
| Native backend cannot reach DB | Use host `DB_PORT=5433`; Docker API still uses internal `5432`. Keep the existing database password. |
| Stack check reaches wrong port | Check process `WEB_PORT` / `CINEDRAFT_WEB_URL` overrides and root `.env`. |
| Tests cannot find contracts | Rebuild `api-tests` using step 7; older images lack `/contracts`. |
| Tests lose schema after rollback | Confirm the updated fixture is present and rebuild the test image. |
| Talent Lab has no versions | Publish a talent build; a raw dataset alone is insufficient. |
| Version label conflict | Choose a new label for changed inputs; do not edit sealed rows. |
| API/catalog returns 503 | Check DB readiness, migration head and `docker compose logs --tail 100 api`. |
| Docker engine unavailable | Start Docker Desktop and verify `docker info`. |

Use `docker compose down` to stop while retaining data. Do not add `-v` unless you intentionally want to delete the database volume.

## Documentation and next phase

- [Setup details](docs/phase-05/setup.md), [calibration walkthrough](docs/phase-05/calibration.md), [implementation summary](docs/phase-05/summary.md) and [verification](docs/phase-05/verification.md).
- [Phase 4 README](README-phase4.md) for earlier import details; use this README for your current ports.
- Next: [Phase 6 — collaboration graph and shared-film evidence](docs/phase-06-handoff.md).
