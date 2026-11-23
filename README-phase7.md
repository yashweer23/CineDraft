# CineDraft — Phase 7

**Server-controlled drafting, exact budget checks and frozen production rosters.** This cumulative VS Code ZIP adds the classic draft API and a hands-on **Draft Inspector**. It preserves the Phase 5 startup fixes, Phase 6 graph, your original game and historical migrations. Updated 25 October 2026.

You can now draft eight distinct people, reroll offers twice, preview and confirm one optional recast, resume saved drafts and finalize production inputs. Every selectable pick must leave a complete affordable roster possible. **Release simulation is Phase 8; this phase does not generate reviews, revenue or profit.**

Save the separately downloaded README as `README.md` at the project root for its relative links to work.

## 1. Upgrade your existing VS Code project

Back up your edits, then merge the ZIP's `CineDraft-VSCode/` contents into your existing project. Open the folder containing `compose.yaml` in VS Code. Keep your three private `.env` files, database password, TMDB credentials and PostgreSQL volume. The ZIP contains environment examples, not your credentials.

| Service | Your address | Configuration |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `.env`: `POSTGRES_PORT=5433`; native `backend/.env`: `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Unchanged prototype service |

For native Vite, keep `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`. Docker still connects internally through `db:5432`, `api:8000` and web port `5173`. No TMDB token belongs in frontend settings.

Use Docker Desktop with Linux containers, Node **24.15+ within 24.x**, and Python **3.12** for native backend development. Unless stated otherwise, run the following in **PowerShell at the project root**:

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
npm run check:stack
```

**Expected migration head: `0004_phase7`.** It adds four tables for guest sessions, compatible drafting catalogs, catalog activations and draft runtime state, plus nullable graph pins on existing drafts. Earlier snapshots remain readable. Rebuild the images before migrating because migrations and CLI scripts are copied into them.

Setup creates missing environment files and preserves existing ones. Fresh installations start with `5432/8000/5173`; adjust the three files to your ports above. See [the Phase 5 port instructions](README-phase5.md#2-confirm-your-ports).

## 2. Choose compatible prices and graph

A new draft needs computed Phase 5 prices and a Phase 6 graph built from the **same sealed dataset**. Existing compatible builds can be reused. List them:

```powershell
Invoke-RestMethod 'http://localhost:8001/api/talent/versions?limit=50' | ConvertTo-Json -Depth 10
Invoke-RestMethod 'http://localhost:8001/api/collaboration/versions?limit=50' | ConvertTo-Json -Depth 10
```

Match their `dataset_id` values. Follow `next_offset` when there are further pages. IDs are not interchangeable:

| Value | Example |
|---|---|
| Source dataset | `tmdb:first-import-v1` |
| Computed pricing version | `pricing:first-ratings-v1` |
| Collaboration graph | `graph:first-graph-v1` |
| New drafting catalog label | `first-draft-v1` |
| Published drafting catalog | `draft-catalog:first-draft-v1` |

If you need builds, use your actual dataset ID:

```powershell
$dataset = 'tmdb:first-import-v1'
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version first-ratings-v1 --dry-run
docker compose run --rm api python -m scripts.build_talent --dataset $dataset --version first-ratings-v1
docker compose run --rm api python -m scripts.build_graph --dataset $dataset --version first-graph-v1 --dry-run
docker compose run --rm api python -m scripts.build_graph --dataset $dataset --version first-graph-v1
```

To import real data, follow [Phase 5's import instructions](README-phase5.md#4-choose-or-import-a-dataset). Drafting itself makes no TMDB requests; it reads your frozen local catalog.

For a practice run without a TMDB key:

```powershell
docker compose run --rm api python -m scripts.seed_demo
docker compose run --rm api python -m scripts.build_talent --dataset fixture:dataset-v1 --version practice-ratings-v1
docker compose run --rm api python -m scripts.build_graph --dataset fixture:dataset-v1 --version practice-graph-v1
```

Use `pricing:practice-ratings-v1` and `graph:practice-graph-v1` below. The synthetic fixture has only eight people, so most roles have short offers and there are no spare people for a completed roster's recast. This is reported honestly; import a larger catalog to explore alternatives. The old handwritten `fixture:pricing-v1` is a persistence demonstration and is intentionally rejected for new drafts.

## 3. Preview and activate a drafting catalog

Set these variables to the compatible IDs you found or created:

```powershell
$pricing = 'pricing:first-ratings-v1'
$graph = 'graph:first-graph-v1'
$draftVersion = 'first-draft-v1'
docker compose run --rm api python -m scripts.prepare_drafting --pricing $pricing --graph $graph --version $draftVersion --dry-run
```

Inspect `minimum_assignment` and `tiers`. The validator matches **distinct people** to all eight slots; it does not add independent role minima. Each tier's talent envelope is 65% of its total budget. An unavailable tier has a reason and cannot be started. No discounts or rescue money are introduced.

Then publish and activate:

```powershell
docker compose run --rm api python -m scripts.prepare_drafting --pricing $pricing --graph $graph --version $draftVersion --activate
Invoke-RestMethod 'http://localhost:8001/api/v1/catalog' | ConvertTo-Json -Depth 10
```

Expect `catalog_id: draft-catalog:first-draft-v1` for the example label. Publishing the same inputs and label is a no-op; activating an already active catalog does not add another activation. Use a new label for changed inputs. Publication without `--activate` creates a catalog but does not select it for new drafts. Dry runs never publish or activate, even if both flags are passed.

The server chooses the active catalog at creation. Existing drafts retain their original dataset, features, prices, graph, rules and scoring specification when you activate another one. The local engine supports up to **5,000 priced person-role profiles per catalog** and rejects larger catalogs explicitly. It does not truncate the pool.

In VS Code, **Terminal → Run Task** also offers **CineDraft: Preview draft catalog** and **CineDraft: Activate draft catalog**. Enter the same pricing, graph and catalog label as above. The React frontend task now uses your port `5174`.

## 4. Draft from the studio

1. Open [the studio](http://localhost:5174), scroll to **Draft Inspector**, and click **Load draft catalog**.
2. Click **Create guest session**. Use **Show token** and save your recovery token privately before refreshing. The token is masked by default and is kept only in the current tab's memory.
3. Choose a genre and an available budget tier, then click **Start draft**.
4. Pick a selectable candidate. The API locks their integer-dollar fee and returns the next saved offer. The order is director, lead, co-lead, supporting 1, supporting 2, writer, cinematographer, composer.
5. Try **Reroll this offer**. There are two successful rerolls for the entire draft. Offers maximize new identities while retaining a legal choice. If no different valid set exists, no allowance is spent.
6. After eight picks, optionally choose a **Recast slot** and click **Preview recast**. Cancelling preserves the roster, spending and recast allowance. Reopening the same slot returns the same cached alternatives.
7. Confirm one replacement, or keep your original roster. A confirmation refunds the old fee and charges the new one atomically, then locks further recasts.
8. Close any open preview and click **Finalize production**. The API saves an immutable input snapshot and displays its SHA-256 hash. Phase 8 will add simulation.

Cards show fictional fees, role-specific strength/genre fit, coverage and up to five ranked works. Synthetic records stay labeled. Missing source years remain unknown. Expand **Inspect locked roster and fees** or **Inspect API state** to see what the server actually saved.

**Resume:** after refreshing or restarting your services, paste the same recovery token into **Restore session**, then open a saved draft. The database retains progress; the browser does not retain the token. Guest access expires after 30 days. Expired, revoked or lost tokens cannot recover access through this phase's API; there is no account login or renewal flow. Expiry does not delete history. Keep this as a local learning build.

**Connection interrupted:** keep the tab open and use **Retry same request**. The inspector preserves the request ID and body in memory until the uncertain action resolves. Do not create a fresh request ID to retry an action whose outcome is unknown. If you must close the tab, save the displayed recovery request separately; it contains no token. See [API recovery](docs/phase-07/api.md).

**Another tab changed the draft:** a stale revision returns `409`. Click **Refresh draft**, inspect the saved state, then choose a new action. A replayed receipt is the original response, so refresh to see later changes.

## 5. Try the identity problem without a database

From `backend/`, with its dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m scripts.assignment_example
```

A synthetic person can write or compose for $100K; another writer costs $400K, another composer $900K. Independent minima incorrectly suggest $200K. The true minimum for **two different people** is $500K. With $600K remaining, hiring the $100K multi-role person as writer is blocked because the remaining composer would cost $900K. Hiring the $400K writer leaves the $100K composer available.

The saved output is [data/phase7-assignment-example.json](data/phase7-assignment-example.json). Edit a copy of the example, change one fee and rerun it. The solver checks exact affordability, including equality at the budget limit.

For native setup, see [Phase 5 native development](README-phase5.md#8-optional-native-development-in-vs-code), then apply `0004_phase7` and run the new preparation command from `backend/`. The native frontend remains:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5174
```

Stop Docker's web container before binding the native frontend to the same port. Root `WEB_PORT` configures Compose and the stack check; the native Vite command needs its own `--port` argument.

## 6. Verify your installation

From the root, with Docker's database running:

```powershell
# Backend unit checks.
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"

# Real PostgreSQL checks, including migrations, concurrent picks and rollback.
docker compose --profile verification run --rm --build api-tests

# Frontend and original game.
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test
npm run check:stack
```

Expected suites: **200 backend unit tests, 52 PostgreSQL integration cases, 22 frontend component tests and 4 original-game tests**. The packaging run passed the unit/component/original-game checks and frontend build. **The 52 PostgreSQL checks were skipped here because no usable PostgreSQL runtime was available.** Migration SQL and function syntax were checked statically; that does not prove runtime constraints or locking. Run the real suite above before relying on draft persistence. No browser visual or full browser-to-database journey is claimed.

The concurrency tests create committed schemas named `phase7_concurrency_<random>` to use separate connections, then drop only their own schema. Other database tests use isolated rolled-back schemas. Your existing data is not a test fixture. See [verification details](docs/phase-07/verification.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Catalog unavailable / no draft tiers | Apply `0004_phase7`, publish computed prices and a graph from the same dataset, then run `prepare_drafting --activate`. |
| No tier is feasible | Inspect the exact minimum assignment and role coverage; publish a revised catalog/pricing version. Do not edit sealed prices. |
| `401 invalid_session` | Restore a valid unexpired token. A draft UUID is not an access token. |
| `404 draft_not_found` | Use the token belonging to that draft. Other sessions cannot read or mutate it. |
| `409 stale_revision` / `stale_offer` | Refresh; use the new revision and currently offered candidate. |
| `409 idempotency_conflict` | A request ID was reused with different fields. Use the original request for retry; a genuinely new action needs a new ID. |
| `422 invalid_candidate` | Choose a selectable person from the current offer. The server rejects invented IDs, client fees and impossible continuations. |
| Recast has no selectable alternatives | Cancel to retain the complete roster. A small frozen pool can have no spare affordable people. |
| API `500`/`503` or request timeout | Check API logs, migration and DB connection; retry the same request ID/body. The server's three-second SQL timeout can require retry under contention. |
| Downgrade refused | Phase 7 draft history exists. Keep the migration and ownership/graph pins; do not remove history to force a downgrade. |
| Port conflict | Preserve host ports `5433/8001/5174`; run only one server on each port. |

Stop with `docker compose down` to preserve the named database volume. Do not add `-v` unless intentionally deleting your data.

## Files to explore

- [Design, exact matching and transactions](docs/phase-07/design.md)
- [API, PowerShell and request recovery](docs/phase-07/api.md)
- [Hands-on exercises](docs/phase-07/hands-on.md)
- [Verification and remaining gates](docs/phase-07/verification.md)
- [Change summary](docs/phase-07/summary.md)
- [Phase 8 handoff: scoring and release simulation](docs/phase-08-handoff.md)

Earlier guides remain in `README-phase1.md` through `README-phase6.md` where applicable and under `docs/`. The original prototype still uses its legacy rules and simulator; the new API has its own state and budgets.
