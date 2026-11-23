# Phase 2 verification

Scope: the new foundation and preserved original prototype. Recorded on 20 October 2026. This report distinguishes implementation from checks actually run in the delivery environment.

## Passed

| Check | Evidence |
|---|---|
| Legacy prototype | Four original application assets unchanged; existing suite passes, covering 540 simulated complete drafts |
| React behavior | Four tests: both services connected, DB failure and recovery, invalid proxy response, integer-dollar planned allocations |
| Frontend build | Strict TypeScript checks and Vite production build pass |
| Backend | Thirteen unit tests pass: liveness, readiness, recovery, error envelopes, CORS, invalid settings, safe errors and OpenAPI readiness contract |
| Live integration | Running Vite proxy reaches a running FastAPI process over HTTP; transformed React module, HTML and OpenAPI JSON respond |
| Unavailable DB | Real PostgreSQL driver attempts connection; API returns the expected sanitized 503 instead of claiming readiness |
| Env setup | Initial files created; a second run preserves all existing settings |
| Alembic baseline | No migration heads; offline upgrade succeeds with an empty transaction |
| Dependency reinstall | Fresh npm ci followed by frontend tests/build passed; a clean Python virtual environment installed the locked requirements and passed all 13 unit tests |
| Package configuration | Markdown links, JSON, YAML structure, Compose build/mount paths and npm manifest/lock agreement checked |

Commands used: root `npm test`; frontend `npm test` and `npm run build`; backend `python -m pytest -q`; the running stack check with **`--allow-db-down` explicitly set**. That flag verifies API connectivity and failure behavior; it does not pass the database connection requirement.

Frontend and backend unit tests use test responses or an injected database double for connected-state cases. The separate PostgreSQL integration test does not use a double or SQLite and remains skipped until a real database is provided.

## Not verified here

1. **Real PostgreSQL success:** no PostgreSQL or Docker runtime was installed. Installing the system database was blocked by environment privilege restrictions. The real integration test was skipped, not passed. Run `python -m scripts.run_integration` from `backend/` with the backend virtual environment after starting your DB.
2. **Docker Compose build/start:** Docker is absent, so the containers were not built or run. Compose structure and referenced paths were reviewed, but that does not prove container startup. Use `docker compose up --build`, then the root stack checker.
3. **Browser visuals and clicks:** no browser executable was installed; the Playwright download did not return a usable browser archive. React DOM tests pass, but browser layout, keyboard behavior and mobile appearance remain manual checks.
4. **GitHub Actions execution:** workflow files are provided; no repository was pushed and no remote CI run was initiated. CI includes a PostgreSQL service and enables the real integration test.
5. **Windows execution:** Windows commands are documented; tests ran on Linux only.

## Runtime and dependencies

Tested: Node v24.19.0; Python 3.12.14. Frontend minimum is Node ^24.15.0 to cover the locked test dependencies. React 19.3.1, Vite 8.3.4, Tailwind 4.3.3, TypeScript 7.0.2, FastAPI 0.155.0, SQLAlchemy 2.1.5 and psycopg 3.3.6 were installed and exercised. Lockfiles are the complete version source of truth.

`frontend/package-lock.json` and `backend/requirements.lock` are included. Container tags receive patch updates within declared major versions; those base images are not immutable digest locks.

## Manual acceptance before Phase 3

- Start the stack and confirm both connection cards show Connected.
- Run the strict root stack checker without `--allow-db-down`.
- Stop PostgreSQL, refresh the check and confirm only readiness fails; restart and verify recovery.
- Open the original prototype on port 5500 and complete a draft.
- Open API docs and try both health routes.
- Inspect the React screen on desktop and mobile; verify keyboard focus and retry.
- Run the real PostgreSQL integration test and record the result in the development log.

The Phase 1 filmography and new draft rules have not been implemented as gameplay. This phase provides their development foundation.
