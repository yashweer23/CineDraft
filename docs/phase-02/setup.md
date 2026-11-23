# Phase 2 — Run it in VS Code

This is the new React/FastAPI/PostgreSQL foundation plus the unchanged original game. The React page checks actual service health. It is not the migrated drafting game yet. You can choose all-Docker startup or edit the frontend/backend as native local processes.

## Prerequisites

- VS Code and **Node.js 24.15+ within the 24.x line**. Tested on 24.19.0; `.nvmrc` records it. The original game alone can still run on Node 22, but the new frontend test dependencies require the newer runtime.
- **Docker Desktop with Compose** for the simplest full stack. Docker must be running.
- **Python 3.12** if running/editing the backend outside Docker.
- Internet for the first dependency/image downloads. A TMDB key is not needed.

Extract the archive to a new folder rather than overwriting an older project containing your personal edits. Open the extracted `CineDraft-VSCode` folder in VS Code. The root contains `package.json`, `compose.yaml`, `frontend/` and `backend/`.

## Option A — all services in Docker

In the VS Code terminal at the project root:

```sh
node scripts/setup-env.cjs
docker compose up --build
```

The first command creates local `.env` files with a generated database password and keeps existing files untouched. It does not print the password. The second command builds and starts PostgreSQL, FastAPI, React/Vite and the original prototype. Keep the terminal open, or add `-d` to run Compose in the background.

| URL | What you should see |
|---|---|
| http://127.0.0.1:5173 | New CineDraft studio screen with API and database status cards |
| http://127.0.0.1:5500 | Original playable drafting game |
| http://127.0.0.1:8000/api/docs | Interactive API docs |
| http://127.0.0.1:8000/api/health | JSON with `status: ok` |
| http://127.0.0.1:8000/api/health/ready | JSON with `status: ready` and `database: connected`, once DB authentication succeeds |

Run `node scripts/check-stack.cjs` from another root terminal. Success verifies the frontend proxy, API and a real PostgreSQL `SELECT 1` query. A 503 means the API is responding but the database is not ready.

Edits in `frontend/src`, `config` and `backend/app` are mounted into the containers; Vite and Uvicorn reload them. Rebuild after changing dependencies or Dockerfiles. The root legacy source is mounted too; save and refresh its browser tab.

Use `docker compose logs api` or `docker compose logs db` to diagnose startup. Stop with Ctrl+C, then `docker compose down`. The named database volume remains; ordinary shutdown does not delete saved database files. Changing the root password after the database volume has already been initialized does **not** change the existing database role's password. Update credentials deliberately rather than deleting your database as a routine fix.

**Verification limit:** Docker is not installed in the delivery environment, so image builds and a live Compose run could not be executed there. The files are provided for local validation; see verification.md for checks that actually passed.

## Option B — edit services locally, use Docker for PostgreSQL

This gives direct access to Python and React processes in your own terminals.

From the project root:

```sh
node scripts/setup-env.cjs
docker compose up -d db
```

### Windows — backend terminal

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

These commands use the virtual environment directly, so PowerShell activation policy changes are unnecessary. If `py -3.12` is unavailable, install Python 3.12 or use the path to your Python 3.12 executable.

### macOS/Linux — backend terminal

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

### Frontend terminal — all platforms

Open a second terminal at the project root:

```sh
cd frontend
npm ci
npm run dev
```

If PowerShell blocks npm scripts, use `npm.cmd ci` and `npm.cmd run dev`. Open http://127.0.0.1:5173. Use Node 24.15+ for compatibility with the locked test environment.

### Optional original-game terminal

From a third terminal at the project root:

```sh
npm start
```

This still starts only the original game at port 5500. The meaning of `npm start` has not changed. Root `npm run dev:frontend` is a convenience alias for the new frontend after its dependencies are installed.

## Option C — no Docker

Install and start PostgreSQL locally (the Compose/CI configuration targets PostgreSQL 17). Create a local login role and database using pgAdmin or your PostgreSQL tools. Then run `node scripts/setup-env.cjs` and edit **backend/.env** to match that database's host, port, name, user and password. The generator creates configuration files; it does **not** create database roles on a native PostgreSQL server.

You can use these SQL statements as a template in your local PostgreSQL admin session, substituting your own local password:

```sql
CREATE ROLE cinedraft WITH LOGIN PASSWORD 'your-local-development-password';
CREATE DATABASE cinedraft OWNER cinedraft;
```

Run the backend/frontend commands from Option B, omitting `docker compose up -d db`. Run `python -m scripts.check_database` with the backend virtual-environment Python from `backend/` to confirm access. No application tables are created by the health check. This native-PostgreSQL route was not executable in the delivery environment.

## Commands to verify your installation

| Location | Command | What it checks |
|---|---|---|
| Root | `npm test` | Preserved legacy engine/server suite; 540 drafts |
| Frontend | `npm test` | React health responses, failures and retry; planned USD allocations |
| Frontend | `npm run build` | Strict TypeScript plus bundled production build |
| Backend | `python -m pytest -q` | Backend health, error, CORS and settings behavior; real DB test skips unless enabled |
| Backend | `python -m scripts.run_integration` | Real PostgreSQL readiness using backend/.env; fails if DB is unavailable |
| Backend | `python -m scripts.check_database` | Read-only `SELECT 1` and a short connection result |
| Root, services running | `node scripts/check-stack.cjs` | Vite → FastAPI → PostgreSQL end-to-end HTTP/database connection |
| Backend | `python -m alembic heads` | Empty migration baseline; no heads expected yet |

Replace `python` with ` .\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on macOS/Linux when not using an activated environment. From the root, the equivalent executable path starts with `backend/`.

The root check script also has `--allow-db-down` for explicitly verifying an API-only setup; it prints that no successful DB check occurred. Do not use that option as evidence of a healthy full stack.

## Troubleshooting

| Symptom | Check |
|---|---|
| Node engine mismatch | Use Node 24.15+ in the 24.x line; restart VS Code after changing Node |
| API unavailable | Backend process, port 8000, and `frontend/.env` API_PROXY_TARGET; restart Vite after env changes |
| API connected, PostgreSQL unavailable | DB process, port, credentials, database existence; `/api/health` alone is not a DB check |
| PostgreSQL port 5432 occupied | Use your existing native instance or change root POSTGRES_PORT and local backend DB_PORT together |
| Startup says invalid config | Run the setup-env script; review backend/.env fields and the JSON syntax of CORS_ORIGINS |
| Docker API cannot reach DB | Inside Docker the DB host is `db`, not `127.0.0.1`; Compose sets this automatically |
| Docker fails due to .env | Run setup-env from the project root first; required root values must exist |
| Database authentication fails after an env edit | Existing volumes retain the original role credentials; env edits do not alter an initialized database |
| Changes to .env do not take effect | Restart the relevant service; the setup script deliberately preserves existing values |
| The original game shows old budget rules | Expected: new rules are still a design preview; future phases migrate the gameplay |
| Blank migrated filmography | No live movie-data integration exists until Phase 4 |

Stop native development servers with Ctrl+C. This package contains no cloud deployment, accounts, paid service setup, or external API token requirement.
