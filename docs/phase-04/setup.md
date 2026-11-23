# Phase 4 setup

Use the root [README](../../README.md) for the short path. Commands below run in PowerShell from the folder containing `compose.yaml` unless stated otherwise.

## Upgrade safely

1. Back up any source changes you made. Extract the cumulative ZIP into a new folder or copy its files over your existing project.
2. Keep your existing root `.env`, `backend/.env`, `frontend/.env` and database volume. The ZIP contains examples, not private `.env` files. If using a new folder, copy your existing three environment files into corresponding paths.
3. The Compose project is still named `cinedraft`, so it uses the existing named volume. Do not run `docker compose down -v` as an upgrade step.
4. Run `node scripts/setup-env.cjs`. It creates missing environment files and preserves existing ones. It does not append newly introduced keys to existing files.
5. Add `TMDB_READ_ACCESS_TOKEN` to `backend/.env` manually. Add or retain `API_PORT` in root `.env` if you use a non-default host API port.

Get the **API Read Access Token** from [TMDB account API settings](https://www.themoviedb.org/settings/api). Paste it into `backend/.env`, never into frontend variables or a chat. The backend reads the token at runtime. API requests from the browser do not receive it. Movie imports use application authentication; this phase does not implement TMDB user login.

```dotenv
# backend/.env: append this without replacing your DB settings
TMDB_READ_ACCESS_TOKEN=your_token_here
```

If your working API port is 8001:

```dotenv
# root .env: preserve all the existing POSTGRES_* values
API_PORT=8001
```

## Docker workflow

Start Docker Desktop and wait until `docker info` succeeds. A Windows `dockerDesktopLinuxEngine` pipe error means the engine is unavailable. Opening VS Code alone does not start it.

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose --profile verification run --rm --build api-tests
```

Expect `0002_phase4 (head)`. On a new database Alembic applies 0001 and 0002; on Phase 3 it adds only 0002. Migration 0001 remains unchanged. The verification service runs 17 PostgreSQL tests using synthetic responses; it never contacts TMDB or needs a token. Temporary test schemas are removed without clearing application data.

`docker compose run --rm api ...` creates a one-off container from the built API image and reads current `backend/.env`. It does not bind the host API port. This is useful for imports after a token change. `docker compose exec api ...` reuses the environment of the running container; recreate that container if its token changed. If Python scripts or migrations change, rebuild the image; only `backend/app` is mounted live.

After the tests pass:

```powershell
docker compose run --rm api python -m scripts.import_tmdb smoke
docker compose run --rm api python -m scripts.import_tmdb start --dataset first-import-v1 --pages 1 --max-movies 20
```

`smoke` makes one live configuration request, validates it and prints a small success object; it does not write the database. It needs backend configuration to load, but does not require a database connection. `start` requires the migrated database. Save its printed `run_id`.

```powershell
$runId = 'paste-the-printed-run-id-here'
docker compose run --rm api python -m scripts.import_tmdb status --run $runId
docker compose run --rm api python -m scripts.import_tmdb review --run $runId
docker compose run --rm api python -m scripts.import_tmdb publish --run $runId
```

Publishing is explicit. Inspect `status_counts`, `review_queue`, `credit_review_queue` and `coverage_warnings` first. The [ingestion guide](ingestion.md) explains review files. An incomplete import can be resumed with the same run ID. A published dataset is immutable; later imports need a new label.

## Open the services

| Service | Default address | Notes |
|---|---|---|
| React studio | http://localhost:5173 | API documentation button follows its proxy |
| FastAPI Swagger | http://localhost:8000/api/docs | Replace 8000 with root `API_PORT` |
| Original game | http://localhost:5500 | Preserved prototype; separate from the imported catalog |
| PostgreSQL | 127.0.0.1:5432 | Host port comes from `POSTGRES_PORT` |

Compose's frontend talks to `http://api:8000` internally regardless of `API_PORT`. If running the frontend with native npm instead, set `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env` when the API uses 8001, then restart Vite.

## Native Python option

Install Python 3.12 and use PostgreSQL 17, either locally or `docker compose up -d db`. Keep `backend/.env` pointed at the host database address and matching password. From the project root:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.run_integration
.\.venv\Scripts\python.exe -m scripts.import_tmdb smoke
.\.venv\Scripts\python.exe -m scripts.import_tmdb start --dataset first-import-v1 --pages 1 --max-movies 20
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Use another free port if needed and match `frontend/.env`. Uvicorn occupies this terminal. In another root terminal run `npm --prefix frontend ci`, then `npm run dev:frontend`; use `npm start` separately for the prototype. On macOS/Linux, use `python3.12` and `backend/.venv/bin/python` instead of the Windows paths.

## Troubleshooting

| Symptom | Action |
|---|---|
| Docker pipe/engine error | Start Docker Desktop's Linux engine; verify `docker info` |
| Host API port already allocated | Keep a free `API_PORT` in root `.env`; recreate API with `docker compose up -d api` |
| Database authentication failure | Restore the existing volume's password; changing environment text does not change that database's password |
| Catalog 503 with healthy API | Run Alembic upgrade and inspect database connectivity; health readiness checks only `SELECT 1` |
| Empty datasets list | Imports remain staging until `publish`; an empty migrated database legitimately has no datasets |
| Token rejected / missing | Check the Read Access Token in backend `.env`; use a fresh one-off container |
| 429 or retry exhausted | Keep the run ID and resume later; successful checkpoints are reused |
| Movie 404 or conflicting source credits | Inspect the source selection; if permanently invalid, start a new label with corrected IDs |
| No eligible films | Inspect exclusions/review queue; use evidence-backed manual review or a different batch |
| Missing images | Source paths may be null; the client must render a placeholder rather than invent an image |

Do not post `.env` contents or full environment dumps when troubleshooting. Safe outputs include migration revision, import run ID and sanitized importer messages.
