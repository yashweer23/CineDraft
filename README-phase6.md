# CineDraft — Phase 6

**Collaboration graph and shared-film evidence.** This cumulative VS Code ZIP adds a versioned graph, offline preview/build commands, six read-only API routes and a **Collaboration Lab** in your studio. It preserves your Phase 5 fixes and all earlier code. Updated 24 October 2026.

Each graph connection belongs to two different people in exact professional roles. Films count once even when a person has multiple matching jobs. The fictional game bonus is `min(12, 4 × shared films)`. Every supporting film remains available after the cap. No shared credits means missing evidence in this dataset, not “never worked together.”

Save the separately downloaded README as `README.md` at the project root to use its relative links.

## 1. Upgrade your existing project

Back up your edits, then merge this ZIP's `CineDraft-VSCode/` contents into your project folder. Open the folder containing `compose.yaml` in VS Code. Preserve your three private environment files and PostgreSQL volume; no private `.env` files are in this ZIP.

Your addresses and environment settings remain:

| Service | Your address | Setting |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `.env`: `POSTGRES_PORT=5433`; native `backend/.env`: `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Existing prototype service |

Keep `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env` for native Vite. Docker still uses `db:5432`, `api:8000` and web container port `5173`. Keep the existing database password and TMDB token.

Use Docker Desktop with Linux containers, Node **24.15+ within 24.x**, and Python **3.12** if running Python natively. Commands below use **PowerShell at the project root** unless noted otherwise.

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
npm run check:stack
```

**Expected migration head: `0003_phase6`.** This new migration adds graph versions, role nodes, edges and film evidence. Historical migrations `0001_phase3` and `0002_phase4` are unchanged. Existing imported datasets, prices and draft snapshots are preserved. Apply the migration before loading Collaboration Lab. Rebuild images because the new CLI and migration files are copied into the image.

Setup only creates missing environment files. For a fresh installation, follow [Phase 5 environment setup](README-phase5.md#2-confirm-your-ports); new defaults are `5432/8000/5173`, so adjust your three files to the ports above after generating them. Existing files are never automatically rewritten.

## 2. Find your dataset ID

A **dataset ID** identifies a published snapshot of imported movies, people and credits. It is not your TMDB token, an import-run UUID or an individual movie ID.

List your published datasets:

```powershell
$catalog = Invoke-RestMethod 'http://localhost:8001/api/catalog/datasets?limit=50'
$catalog.items | Select-Object id, source
```

You can also run `GET /api/catalog/datasets` in Swagger. Copy the exact `id` from the response. If there are more than 50 datasets, follow `next_offset` with the endpoint's `offset` parameter. For example, a completed import named `first-import-v1` normally has ID `tmdb:first-import-v1`.

If the list is empty, complete the [TMDB import and publication steps](README-phase5.md#4-choose-or-import-a-dataset), or use this explicit synthetic practice dataset:

```powershell
docker compose run --rm api python -m scripts.seed_demo
```

Its dataset ID is `fixture:dataset-v1`. The fixture contains eight fictional people and one movie; all eligible pairs share that movie. It is labeled synthetic throughout. It yields **9 role nodes, 35 role-pair connections and 35 film-evidence rows**. One person has two roles, but there is no self-connection.

Phase 6 needs a sealed dataset. It does not require a new Phase 5 ratings build or any live TMDB requests.

## 3. Preview, then publish the graph

Replace the dataset example with the ID you found. Use `fixture:dataset-v1` if you chose the practice option:

```powershell
$dataset = 'tmdb:first-import-v1'
$graphVersion = 'first-graph-v1'
docker compose run --rm api python -m scripts.build_graph --dataset $dataset --version $graphVersion --dry-run
```

Review `report`: role nodes, connections, film evidence, isolated profiles and capped edges. A dry run writes no graph rows. Then publish:

```powershell
docker compose run --rm api python -m scripts.build_graph --dataset $dataset --version $graphVersion
```

| Identifier | Example | Used for |
|---|---|---|
| Dataset ID | `tmdb:first-import-v1` | Frozen input movies, people and credits |
| CLI version label | `first-graph-v1` | Your name for this graph build |
| Published graph ID | `graph:first-graph-v1` | Studio selection and API requests |

A successful build reports `created: true`. Run the same command again to confirm `created: false` and the same `graph_hash`. New source data or changed graph parameters require a new label. Labels begin with a lowercase letter or digit and contain 1–71 lowercase letters, digits, underscores or hyphens.

Publication is atomic: the graph, nodes, edges and evidence become visible together. A failed build rolls back the new graph. Existing sealed versions remain unchanged. The API never imports data or builds graphs at startup.

## 4. Explore Collaboration Lab

1. Open [the studio](http://localhost:5174) and scroll below Talent Lab to **Collaboration Lab**.
2. Click **Load collaboration graphs**, then choose your published graph.
3. Filter connections by a professional role and click **Inspect shared films**.
4. Inspect the names, roles, shared-film count, game bonus and exact jobs for both people on each film. Use **Next shared films** to inspect all evidence, including films beyond the bonus cap.
5. Under **Check a specific pair**, search your catalog and select each person's credited role. Click **Compare credited roles**.
6. Try the same person's writer and director profiles separately. Their supporting films may differ. A person cannot be selected on both sides.

Only source-backed film evidence is displayed. Missing years remain “Year unavailable,” synthetic data is labeled, and real TMDB movies link to their source page. The graph does not claim friendship or artistic compatibility. The bonus is a game rule; full team chemistry and authoritative drafting are not activated by this phase.

After publishing another graph, use **Refresh collaboration graphs**. Talent Lab and the original game remain available.

## 5. Try the arithmetic without a database

With backend dependencies installed, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.graph_example
```

This explicitly synthetic example has six shared director–actor films, one writer–actor film and no writer–composer overlap. Expected bonuses are **12, 4 and 0**. All six director–actor films remain in the output. A saved copy is in [data/phase6-graph-example.json](data/phase6-graph-example.json).

For installing native dependencies and starting the API/frontend in VS Code, see [native development](README-phase5.md#8-optional-native-development-in-vs-code). Use the new migration head before testing. The frontend command remains:

```powershell
npm --prefix frontend run dev -- --port 5174
```

Stop Docker's web service before binding a native frontend to the same port. Native backend commands use `backend/.env` and port `8001`; the DB host port is `5433`.

## 6. Verify locally

From the root, with your Docker database running:

```powershell
# Backend unit tests.
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"

# Real PostgreSQL integration tests, including graph rollback and immutability.
docker compose --profile verification run --rm --build api-tests

# Original game.
npm test

# Frontend tests and build. No root npm install is needed.
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend

# Frontend -> API -> database.
npm run check:stack
```

Expected suites: **141 backend unit tests**, **37 PostgreSQL integration tests**, **14 frontend tests**, **4 original-game tests**. Your Phase 5 savepoint isolation, contract files in the test image, writable cache and port-aware check script are preserved.

The package's unit/component checks and build are verified; real PostgreSQL tests require your machine or CI. They were not run in this packaging environment. Your earlier 22 passing database tests are recorded as Phase 5 results, not evidence that the new migration has passed. See [verification](docs/phase-06/verification.md) for the exact checks and limitations.

## Troubleshooting

| Symptom | Action |
|---|---|
| “Published Phase 6 graph version not found” | Use the exact graph ID from `/api/collaboration/versions`; publish the build first. |
| No graphs appear | A sealed dataset alone is insufficient: run `scripts.build_graph`, then refresh. |
| Collaboration API returns 503 | Rebuild the API, apply `0003_phase6`, and check `docker compose logs --tail 100 api`. |
| No shared films for a pair | Verify both selected roles and dataset coverage. Zero evidence is valid. |
| A role is missing from the picker | The selected dataset has no eligible mapped film credit for that person in that role. |
| Same-person pair rejected | Select different people; separate roles do not create separate identities. |
| Graph version label conflict | Use a new label for changed inputs or incomplete manual output. |
| Graph exceeds observation limit | The initial builder rejects more than 500,000 pair/movie observations before publishing. Use a smaller sealed dataset; it never silently drops edges. |
| Port conflict | Keep host ports `5433/8001/5174`; do not run Docker and native servers on the same host port. |
| Contract files missing during tests | Rebuild `api-tests` with `--build`; the image copies contracts to `/contracts`. |

Stop safely with `docker compose down`, preserving the database volume. Do not add `-v` unless intentionally deleting your data.

## Read and experiment

- [Graph design and persistence](docs/phase-06/design.md)
- [API reference and PowerShell examples](docs/phase-06/api.md)
- [Hands-on exercises](docs/phase-06/hands-on.md)
- [Verification and limitations](docs/phase-06/verification.md)
- [Implementation summary](docs/phase-06/summary.md)
- Next: [Phase 7 — authoritative drafting and budget feasibility](docs/phase-07-handoff.md)
