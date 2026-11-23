# CineDraft — Phase 2 VS Code project

A movie drafting game you can develop locally, one phase at a time. This pack includes the **React + TypeScript + Tailwind frontend, FastAPI backend, PostgreSQL configuration and development tools**, alongside the original playable prototype and every Phase 1 document.

Implemented: the full-stack foundation and service-health screen. Future work: real movie data, the authoritative draft engine, top-five film cards, new simulations and accounts. Live PostgreSQL, Docker and visual-browser verification could not be completed here; see the verification report.

## Start Phase 2

Extract the ZIP and open the inner `CineDraft-VSCode` folder in VS Code. Use **Node 24.15+ in the 24.x line** and a running Docker Desktop installation. From the root terminal:

```sh
node scripts/setup-env.cjs
docker compose up --build
```

Open **http://127.0.0.1:5173** for the new studio screen. Once PostgreSQL is reachable, both status cards should show **Connected**. The original game is at **http://127.0.0.1:5500**. API documentation is at **http://127.0.0.1:8000/api/docs**.

For native Python/React development or a setup without Docker, follow [the complete VS Code setup guide](docs/phase-02/setup.md). It includes Windows commands, database setup, expected responses and troubleshooting. No TMDB key is needed until Phase 4.

## Original game

Root `npm start` still starts the original game at port 5500 without dependency installation or a database. Its four source files and old gameplay rules are preserved. The new React page is a separate foundation screen, not the migrated game.

The $10M/$50M/$200M cards use integer USD with 35% production reserves in the shared design configuration. They are clearly labeled previews. The two-reroll, one-recast and top-five filmography rules are still for later implementation.

## Project map

| Path | Purpose |
|---|---|
| frontend/src/App.tsx | React studio screen and retry controls |
| frontend/src/api.ts | Actual health requests, timeout, cancellation and response validation |
| backend/app/main.py | FastAPI factory, health routes and error handling |
| backend/app/config.py | Typed environment settings |
| backend/app/database.py | SQLAlchemy/psycopg connection and SELECT 1 |
| backend/migrations/ | Empty Alembic baseline; domain schema starts in Phase 3 |
| config/game-design.json | Planned rules metadata, not an active drafting engine |
| scripts/setup-env.cjs | Generate local env files without overwriting existing values |
| scripts/check-stack.cjs | Verify Vite → FastAPI → PostgreSQL when running |
| compose.yaml | Local database, API, frontend and original game |
| index.html, app.js, engine.js, styles.css | Unchanged original playable prototype |

## Check it

```sh
# Root — original prototype checks
npm test

# Root — strict connection check after the full stack is running
node scripts/check-stack.cjs

# Root — after installing frontend dependencies with npm ci in frontend/
npm --prefix frontend test
npm --prefix frontend run build
```

From `backend/`, use the virtual-environment Python to run `python -m pytest -q`. Run `python -m scripts.run_integration` to enable the real PostgreSQL check using your local settings. Without a DB, that separately gated test is skipped.

Verified here: React tests/build, backend unit checks, the original 540-draft checks and a live Vite-to-FastAPI request. The expected database-unavailable response was verified. A successful live PostgreSQL connection, Docker run, remote GitHub CI run and visual browser checks are not claimed.

## Documentation and next step

- [Phase 2 setup](docs/phase-02/setup.md), [summary](docs/phase-02/summary.md), [verification](docs/phase-02/verification.md).
- [Phase 1 rulebook](docs/phase-01/game-rulebook.md), [scoring design](docs/phase-01/scoring-design.md), [talent data](docs/phase-01/talent-data-spec.md).
- [UI/UX blueprint](docs/phase-01/ui-ux-blueprint.md), [state and edge cases](docs/phase-01/game-state-and-edge-cases.md), [Phase 1 summary](docs/phase-01/phase-01-summary.md).
- [Complete roadmap](docs/CineDraft_Development_Roadmap.md) and [Phase 3 handoff prompt](docs/phase-03-handoff.md).
- [Original README](README-phase1.md), [hands-on guide](docs/hands-on-guide.md), [prototype audit](docs/prototype-audit.md), [development log](docs/development-log.md).

Before Phase 3, run the full setup locally and get both cards connected. Phase 3 adds normalized database models, migrations and API contracts. This ZIP does not deploy a site or configure a cloud service.
