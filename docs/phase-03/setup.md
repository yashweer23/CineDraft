# Phase 3 setup — Windows and VS Code

## Upgrade without losing local settings

1. Keep a backup of your existing project and any edits. Extract this cumulative ZIP.
2. Use the new source files with your existing `.env`, `backend/.env` and `frontend/.env`. They are not bundled in the ZIP. Preserve the existing PostgreSQL volume.
3. Open the project root in VS Code. Start Docker Desktop and wait for the Linux engine.
4. Run the commands below from the root. `docker info` must show a reachable Server before Compose can work.

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic current
node scripts/check-stack.cjs
```

`0001_phase3 (head)` confirms this migration. You should then get the API/database connection success from the checker. The migration adds domain tables; it does not reset the database. The API does not run migrations at startup. Re-running `upgrade head` at the current head is safe.

The root Compose project name remains `cinedraft`. If using a new extraction folder with an existing volume, copy the old `.env` first so the password still matches. If a password mismatch appears, restore the existing credentials; deleting a volume is not the troubleshooting step.

## Explore synthetic data

```powershell
docker compose exec api python -m scripts.seed_demo
docker compose exec api python -m scripts.inspect_demo
docker compose --profile verification run --rm --build api-tests
```

Expected fixture summary: `synthetic: true`, `people: 8`, `role_profiles: 9`, `talent_spend_usd: 850000`. A second seed prints `created: false`. It preserves the original fixture. The handwritten fixture result is explicitly synthetic and is not a completed simulation engine.

The test image includes pytest; the normal API image only installs runtime packages. The verification service uses the same PostgreSQL connection settings but creates unique temporary schemas, performs tests, and rolls back each schema. It requires the normal database-owner privileges used in this local project. If the command cannot connect, it fails; it does not report skipped integration checks as a successful database run.

To view logs or stop containers while retaining the database:

```powershell
docker compose logs --tail 100 api db
docker compose stop
```

## Native Python development

You can use the existing Phase 2 virtual environment. From the root on Windows:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m scripts.seed_demo
.\.venv\Scripts\python.exe -m scripts.inspect_demo
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.run_integration
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

If `.venv` already exists, skip its creation. PostgreSQL must already be running and `backend/.env` must match. Avoid running a native API on port 8000 while the Compose API is using that port. The [Phase 2 guide](../phase-02/setup.md) covers native React and a fully native PostgreSQL installation. On macOS/Linux use `python3.12 -m venv .venv` and `.venv/bin/python`.

From a second root terminal:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

## Inspect contracts offline

In VS Code open `contracts/openapi.proposed.json` and `contracts/schemas.json`. The live `/api/docs` intentionally lists only health endpoints. To regenerate the files after editing the Pydantic contracts, run from `backend/` with its virtual environment:

```powershell
.\.venv\Scripts\python.exe -m scripts.export_contracts
```

## Troubleshooting

| Symptom | Next action |
|---|---|
| `dockerDesktopLinuxEngine` pipe missing | Start/restart Docker Desktop and wait for its Linux engine; check `docker info` |
| Docker Desktop reports a WSL startup error | Resolve the specific Desktop error before running Compose; application changes cannot start the missing engine |
| `relation ... does not exist` when seeding | Run `alembic upgrade head` against the same database |
| Both status cards Connected, no tables | Connectivity checks use `SELECT 1`; apply the migration explicitly |
| `/api/v1/drafts` returns 404 | Expected in Phase 3: game routes are contracts only |
| Existing database rejects password | Preserve/restore the prior `.env` values used to initialize it |
| Integration tests are skipped in plain pytest | Run `python -m scripts.run_integration` or the Compose verification command to enable real DB tests |
| Duplicate/incomplete fixture already present | Inspect it; the seed command deliberately refuses to overwrite partial records |

A downgrade implementation is included for isolated migration tests, but it drops Phase 3 tables and data. Do not run it on a project database containing work you want to keep. No downgrade is needed to install this phase.
