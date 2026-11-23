# Phase 5 setup and Windows commands

Start with the root [README](../../README.md). These commands assume PowerShell and a terminal at the project root unless stated otherwise.

## Keep your working configuration

Retain root `.env`, `backend/.env`, `frontend/.env`, database password and Docker volume. The setup script creates missing files only. There are no secret `.env` files in the ZIP. Rebuild the images after upgrading because CLI scripts are copied into the API image.

Your working Windows host ports are PostgreSQL `5433`, API `8001` and studio `5174`. Keep these values in root `.env`:

```dotenv
POSTGRES_PORT=5433
API_PORT=8001
WEB_PORT=5174
```

Compose maps PostgreSQL to `127.0.0.1:${POSTGRES_PORT:-5432}:5432`, the API to `127.0.0.1:${API_PORT:-8000}:8000` and web to `127.0.0.1:${WEB_PORT:-5173}:5173`. The Docker API keeps database port `5432`; the Docker frontend keeps `http://api:8000`. For native commands, use `DB_PORT=5433` in `backend/.env` and `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`. Restart native servers after changing their environment files. Setup preserves existing files, so changing the root file does not automatically update them.

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

Expected migration: `0002_phase4 (head)`. Expected local integration suite: **22 passed**, with unrelated unit tests deselected. There is no Phase 5 DDL change. Existing immutable feature/pricing tables have enough structure to hold the computed profiles, evidence and manifests.

## Select a dataset

In Swagger, run `GET /api/catalog/datasets`. Choose the exact ID of a sealed version. A staging TMDB import is not usable until you review and publish it. If the list is empty, finish the [Phase 4 workflow](../phase-04/setup.md) or use the explicitly synthetic fixture:

```powershell
docker compose run --rm api python -m scripts.seed_demo
```

The fixture dataset ID is `fixture:dataset-v1`. It already has handwritten Phase 3 prices for its persistence exercise; a Phase 5 build writes separate versions and leaves those values unchanged.

## Preview and publish

```powershell
$dataset = 'tmdb:first-import-v1' # replace with your exact dataset ID
$version = 'first-ratings-v1'
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version $version --dry-run
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version $version
```

The preview calculates the complete output and reports hashes, counts and fees without database writes. The second command recomputes from the same immutable input, inserts feature rows, seals the feature version, inserts prices, seals the pricing version, and commits once. An error rolls back both new versions. The token can stay in backend `.env`, but these commands do not use it or contact TMDB.

Labels accept 1–71 lowercase letters, digits, underscores or hyphens. A label maps to `features:LABEL` and `pricing:LABEL`. Repeating a matching successful build returns `created: false`. Reusing a label for different or incomplete output fails; choose a new label instead of modifying sealed rows.

Use **Load talent catalog** in the studio at http://localhost:5174. If you published while the page was open, click **Refresh talent catalog**. API docs are at http://localhost:8001/api/docs; the old prototype is still at http://localhost:5500. The connection check reads process `WEB_PORT`, then root `.env`, then defaults to `5173`; `CINEDRAFT_WEB_URL` overrides the entire address.

## Native Python and frontend

Use Python 3.12 and Node 24.15+ within the 24.x line. Stop Docker's API and frontend to free their host ports, retaining PostgreSQL. From the root:

```powershell
docker compose stop api web
docker compose up -d db
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

There are no root npm dependencies to install. Configure `backend/.env` for your actual PostgreSQL host/port/password. From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.run_integration
.\.venv\Scripts\python.exe -m scripts.build_talent --dataset tmdb:first-import-v1 --version first-ratings-v1 --dry-run
.\.venv\Scripts\python.exe -m scripts.build_talent --dataset tmdb:first-import-v1 --version first-ratings-v1
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8001
```

In another root terminal, run `npm --prefix frontend run dev -- --port 5174`. Native Vite needs this explicit argument; root `WEB_PORT` configures Compose and the check script. The original prototype may stay in Docker; to run it natively, first `docker compose stop prototype`, then `npm start` at the root. On macOS/Linux, use `.venv/bin/python` and an appropriate Python 3.12 launcher.

## Troubleshooting

| Symptom | Action |
|---|---|
| Docker Linux engine pipe missing | Start Docker Desktop and verify `docker info` |
| Port 8000 already allocated | Set a free `API_PORT` in root `.env`, then recreate the API container |
| Port 5173 occupied by another project | Keep `WEB_PORT=5174`; recreate Docker web or start native Vite with `--port 5174` |
| Native backend cannot connect | Match `backend/.env` DB_PORT to host `POSTGRES_PORT=5433`, not Docker's internal port |
| Contract tests cannot find files | Rebuild the test image; it now copies contracts to `/contracts` |
| Talent Lab has no versions | Publish a talent build, then refresh; a raw dataset alone is insufficient |
| Handwritten fixture prices absent from Talent Lab | Expected: only computed Phase 5 versions appear |
| Existing sealed dataset required | Use the exact dataset ID from `/api/catalog/datasets`, and publish staging imports first |
| No eligible mapped credits | Inspect the import coverage report; use a corrected/new dataset |
| Version label conflict | Keep the older build and choose a fresh label |
| Catalog 503 | Verify migration head, DB connectivity and that the rebuilt API is running |
| Low coverage / genre catalog gap | Inspect evidence; do not mistake a prior-based value for observed skill |
| New files seem ignored by Docker | Run `docker compose up --build -d`; CLI and migration files are copied into images |
| `pytest` skips integration tests | Run `scripts.run_integration` or the Compose verification service against PostgreSQL |

If a build fails, existing versions and games remain available. Do not delete the volume or change an existing database's password as a troubleshooting shortcut.
