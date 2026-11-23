# CineDraft — Phase 3 VS Code project

Phase 3 adds **21 PostgreSQL tables, an Alembic migration, immutable data snapshots, typed API contracts, synthetic fixtures and database exercises**. This is a cumulative project: the React studio, FastAPI health checks, original playable game and every earlier document are included.

The new database layer is implemented. Game endpoints are defined in a separate proposed OpenAPI file; they are not live. TMDB ingestion is Phase 4. The authoritative draft engine is Phase 7. The release simulator is Phase 8.

## Updating your Phase 2 folder

Back up any edits you made. Copy the extracted project files into your existing CineDraft folder, retaining your existing root `.env`, `backend/.env`, `frontend/.env` and PostgreSQL Docker volume. The ZIP contains no `.env` secrets. Do not delete the database volume or generate a different password for the existing database.

Alternatively, extract into a new folder and copy those three existing `.env` files into their corresponding locations before starting. The Compose project name remains `cinedraft`, so it uses the same project database volume.

## Run Phase 3

Open the folder containing `compose.yaml` in VS Code. Use Node 24.15+ in the 24.x line. **Start Docker Desktop and wait for its Linux engine** before using Compose. Your previous `dockerDesktopLinuxEngine` pipe error means Docker's engine was unreachable; opening VS Code does not start Docker Desktop.

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic current
```

Expected migration: `0001_phase3 (head)`. The environment generator preserves existing files. Migrations are explicit: starting the API does not create tables automatically.

Open the studio at http://localhost:5173, the original game at http://localhost:5500, and the running health API documentation at http://localhost:8000/api/docs. The two Connected cards prove connectivity, not schema migration success; use `alembic current` to check the schema.

## Hands-on database exercise

```powershell
docker compose exec api python -m scripts.seed_demo
docker compose exec api python -m scripts.inspect_demo
docker compose --profile verification run --rm --build api-tests
```

The first command inserts an explicitly synthetic dataset: eight fictional people, one fictional film, nine role profiles, eight offers/picks, saved actions and one frozen result. The director also has a writing credit but is picked only once. No TMDB IDs, real salaries, images or movie data are fabricated. Re-running the fixture command is a no-op after a complete successful run.

The final command runs real PostgreSQL integration tests in temporary schemas, rolled back afterward. It does not clear your application tables. You can use the matching commands from **Terminal → Run Task** for migration, seeding and snapshot inspection.

## Project map

| Path | What to explore |
|---|---|
| `backend/app/models.py` | SQLAlchemy models and relational constraints |
| `backend/migrations/versions/0001_phase3.py` | Frozen table definitions and PostgreSQL immutability triggers |
| `backend/app/contracts.py` | Validated requests, candidate cards, budgets, snapshots and results |
| `backend/app/repository.py` | Canonical hashes, stored response lookup and snapshot/result persistence |
| `backend/app/fixtures.py` | Explicit synthetic, repeatable persistence exercise |
| `contracts/openapi.proposed.json` | Future game endpoints; NOT mounted in the running API |
| `contracts/schemas.json` | Reusable JSON schemas |
| `docs/phase-03/` | Setup, schema, API semantics, exercises and verification |
| `frontend/` | Preserved studio health flow, now labeled Phase 3 |
| `index.html`, `app.js`, `engine.js`, `styles.css` | Unchanged original playable prototype |

Root `npm start` still runs only the original prototype on port 5500. It does not start React or the new backend.

## Guides and verification

- [Phase 3 setup and Windows commands](docs/phase-03/setup.md)
- [Database design and diagrams](docs/phase-03/database-design.md)
- [API contract and transaction rules](docs/phase-03/api-contracts.md)
- [Hands-on exercises](docs/phase-03/hands-on.md)
- [Implementation summary](docs/phase-03/summary.md) and [verification report](docs/phase-03/verification.md)
- [Phase 4 handoff](docs/phase-04-handoff.md): TMDB ingestion
- [Phase 1 specifications](docs/phase-01/phase-01-summary.md), [Phase 2 setup](docs/phase-02/setup.md), [complete roadmap](docs/CineDraft_Development_Roadmap.md)

Backend unit/contract tests, frontend tests/build, original-game tests, and offline migration SQL checks pass in the delivery environment. Real PostgreSQL migration/constraint tests and the Docker build cannot run here and remain local/CI gates. See the verification report for exact counts and limits.
