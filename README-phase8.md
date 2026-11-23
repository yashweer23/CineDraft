# CineDraft — Phase 8

**Scoring and release simulation from frozen production inputs.** This cumulative VS Code ZIP adds deterministic studio scores, simulated reviews, fictional financial outcomes, four-week box office and a saved **Release Report**. Your existing port fixes, drafts, datasets, prices, graph versions and original game are preserved. Updated 27 October 2026.

Phase 7's finalized rosters can now be released. The server calculates one result per film from its saved inputs and seed. Repeating a request or retrying a failed simulation cannot reroll the outcome. Scores, reviews, fees and revenue remain fictional game constructs, not predictions about real people or films.

Save the separate README as `README.md` at your project root for relative links to work.

## 1. Upgrade your existing project

Back up your edits, then merge the ZIP's `CineDraft-VSCode/` contents into your existing VS Code folder. Preserve your three private `.env` files, database password, TMDB credentials and PostgreSQL volume. No private environment files are included in the ZIP.

| Service | Your address | Keep this setting |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `.env`: `POSTGRES_PORT=5433`; native `backend/.env`: `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Unchanged prototype service |

For a native frontend, keep `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`. Docker continues using `db:5432`, `api:8000` and container web port `5173` internally.

Use Docker Desktop with Linux containers, Node **24.15+ within 24.x**, and Python **3.12** for native Python commands. Run these in **PowerShell at the project root**:

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
npm run check:stack
```

**Expected migration head: `0005_phase8`.** It adds an immutable simulation-attempt table and consistency guards for new results, bringing the schema to 32 tables. Earlier migrations are unchanged. Apply the migration before using release endpoints. Images must be rebuilt because migrations and scripts are copied into them.

Existing Phase 7 catalogs and finalized drafts work without rebuilding prices, graphs or inputs. The frozen `scoring:baseline-1.0` configuration is preserved and is now executed by `simulation-1.0`.

Setup preserves existing environment files. On a fresh installation, adjust generated defaults to your ports above; see [Phase 5 environment setup](README-phase5.md#2-confirm-your-ports). Never remove the database volume as an upgrade step.

## 2. Restore a draft or prepare your first one

If you already completed Phase 7:

1. Open [the studio](http://localhost:5174) and scroll to **Draft Inspector**.
2. Paste your saved recovery token into **Restore session**.
3. Open your saved draft. Complete its eight picks and close any recast preview.
4. Click **Finalize production** if you have not already finalized it.

Guest tokens remain valid for 30 days from creation, can be revoked, and are stored only in tab memory. Keep your token privately before refreshing. A new token does not inherit another session's drafts. Expiry, revocation or token loss does not delete history, but this phase does not add account recovery or renewal.

If you need a new drafting catalog, follow [the Phase 7 guide](README-phase7.md). For a complete synthetic practice setup without a TMDB key:

```powershell
docker compose run --rm api python -m scripts.seed_demo
docker compose run --rm api python -m scripts.build_talent --dataset fixture:dataset-v1 --version practice-ratings-v1
docker compose run --rm api python -m scripts.build_graph --dataset fixture:dataset-v1 --version practice-graph-v1
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --dry-run
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --activate
```

Review enabled tiers in the dry run. In the inspector, load the catalog, create a guest session, save its token, choose an available tier and draft eight distinct people. The practice fixture has only eight people, so short offers and unavailable recast alternatives are expected. It is explicitly labeled synthetic.

Real imported catalogs work through the same flow. Release simulation reads your local frozen snapshot; it makes no TMDB requests and does not refresh data, re-price hires or change a roster.

## 3. Run and inspect a release

After finalization, the new **Release Report** section appears below the draft controls.

1. Click **Run release simulation**.
2. Read the **Studio score**, **Simulated critics** and **Simulated audience** separately.
3. Inspect **Why this score?** for the genre, talent, chemistry and budget-efficiency contributions. Top weighted genre contributors are identified by name and slot.
4. Inspect production, marketing, total cost, theatrical gross, studio receipts and profit. Profit includes marketing; gross is not studio income.
5. Review the four-week chart. All four integer-dollar values sum exactly to the saved theatrical gross.
6. Expand **The twelve chemistry relationships**. Inspect shared films to see the pinned graph's titles and exact jobs for each person. Every film remains accessible after the bonus cap.
7. Read source coverage notes, then expand the saved reproducibility record to inspect versions, input/output hashes, frozen seed and named random draws.

The result persists in PostgreSQL. Restore the same session and open the draft later to read it again. Successful films have no reroll or re-release action.

### Understand the numbers

| Measure | What it means |
|---|---|
| Studio score | Deterministic weighted score: 30% genre + 30% talent + 25% chemistry + 15% efficiency, rounded half-up |
| Chemistry | Neutral 60 plus capped bonuses from exactly twelve designated roster relationships; maximum 100 |
| Simulated reviews | Separate game outputs with bounded, seeded noise; not TMDB source ratings |
| Committed production | Reserved production money + locked talent fees; unused talent authorization is excluded |
| Marketing | 20% of committed production, modeled as an additional cost |
| Worldwide theatrical gross | Simulated theatrical revenue, not studio receipts |
| Studio receipts | 50% of gross in this baseline model |
| Profit | Receipts − committed production − marketing |
| Return on total cost | Profit divided by production + marketing, as a percentage |

The budget controls production and talent allocation. Marketing is an additional modeled release cost; it is not secretly deducted from the remaining talent balance. Studio score has no direct gross-revenue or profit bonus. See [the formulas](docs/phase-08/design.md) for exact arithmetic and limitations.

## 4. Handle retries correctly

There are two different situations:

- **A request times out or the connection drops:** keep the tab open and click **Retry same request**. The inspector reuses its exact command ID and body. The database may already have committed, so do not issue a new command to guess what happened.
- **The server confirms `simulation_failed`:** the failed attempt is saved and no result exists. Click **Retry failed simulation** after addressing an engine issue. This is a new command at the new revision, but it uses the same immutable snapshot, seed and deterministic simulation ID.

An older receipt stays unchanged even after a later retry succeeds. Use **Refresh draft** to see the latest state. A 409 stale revision means another action already changed the draft; refresh before choosing a new action.

The simulation runs synchronously in one database transaction. A process crash or SQL write failure rolls back uncommitted state, result, attempt and receipt together. There is no background queue or permanently committed “running” job in this phase. A confirmed computation failure is a successful command response describing a failed simulation; it does not invent a partial result.

## 5. Try the arithmetic without PostgreSQL

With backend dependencies installed, run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.simulation_example
```

The example uses invented people, fees, features and a fixed seed. It does not import or publish data. Expected output for the bundled example:

| Output | Value |
|---|---:|
| Studio score | 66 |
| Simulated critics | 70.22 |
| Simulated audience | 60.32 |
| Committed production | $6,750,000 |
| Marketing | $1,350,000 |
| Worldwide theatrical gross | $20,008,096 |
| Studio receipts | $10,004,048 |
| Profit after marketing | $1,904,048 |
| Weekly gross | $8,638,080; $5,539,493; $3,552,407; $2,278,116 |

A saved copy is [data/phase8-simulation-example.json](data/phase8-simulation-example.json). Run it twice and compare the output hashes. In a local copy, change only the seed: the reviews and financial outcome can change while the studio score remains the same.

For native setup, use [the existing native-development instructions](README-phase5.md#8-optional-native-development-in-vs-code), then apply `0005_phase8`. The frontend command remains:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5174
```

Stop Docker's web container before using the same port natively. Root `WEB_PORT` controls Compose and the stack check; Vite's native command needs `--port 5174`.

## 6. Verify a saved result from VS Code

Copy your released draft UUID from the inspector, then run from the project root:

```powershell
$draftId = 'PASTE-YOUR-RELEASED-DRAFT-UUID'
docker compose run --rm api python -m scripts.verify_release --draft $draftId
```

Expected: `matched: true`, `writes: 0`, `upstream_requests: 0`. This operator command reads the frozen snapshot and saved result, recomputes the result locally, and compares the full JSON and output hash. It uses your backend's database credentials; it does not require or print the guest token. It does not update the result or query live TMDB data.

VS Code's **Terminal → Run Task → CineDraft: Verify saved release** prompts for the UUID. The native equivalent, from `backend/`, is `python -m scripts.verify_release --draft UUID`.

## 7. Run the checks locally

From the project root:

```powershell
# Backend unit checks.
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"

# Real PostgreSQL constraints, rollback, replay and concurrent releases.
docker compose --profile verification run --rm --build api-tests

# Frontend and original game.
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test
npm run check:stack
```

The package has **258 backend unit cases, 64 PostgreSQL integration cases, 30 frontend component cases and 4 original-game cases**. Unit/component/original-game checks and the frontend build passed during packaging. Migration SQL and function syntax were also parsed.

**The 64 PostgreSQL cases were skipped here because no usable PostgreSQL runtime or test connection was available.** They include the prior 52 cases and 12 new release/concurrency cases. Static parsing does not prove database constraints or locking. Run the real suite above before relying on the new persistence flow. Full browser-to-database and visual browser verification also remain local checks. Details: [verification report](docs/phase-08/verification.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Release controls are missing | Complete eight picks, cancel any open preview and finalize production. Reload the updated frontend. |
| Release/status API returns 503 | Rebuild images, apply `0005_phase8`, check DB connectivity and API logs, then retry the exact interrupted request. |
| `unsupported_simulation_input` | The engine rejected an unsupported or inconsistent frozen input. Existing data is preserved. Do not edit the snapshot or silently re-price the roster. |
| `simulation_failed` | Check API logs for the error type. A confirmed failure can be retried with the same inputs after the cause is fixed. |
| `invalid_release_state` | Release requires finalized inputs. A new simulation retry requires a confirmed failed state. Successful results cannot be rerolled. |
| Another tab changed the draft | Refresh the draft to load its current revision before a new command. |
| `401` / `404 draft_not_found` | Restore the valid owner token. Knowing a draft UUID does not grant access. |
| Shared-film evidence is unavailable | The result remains saved. Check the pinned graph endpoint; refreshing the report never resimulates the film. |
| Replay reports `matched: false` | Preserve the stored input/output and inspect version or engine differences. Do not overwrite history to make a comparison pass. |
| Downgrade is refused | Phase 8 release history exists. The guard protects attempt history and result consistency. |

Stop with `docker compose down` to retain the volume. Do not use `down -v` as a routine upgrade or troubleshooting step.

## Read and experiment

- [Scoring, random streams and transaction design](docs/phase-08/design.md)
- [API and PowerShell examples](docs/phase-08/api.md)
- [Hands-on exercises](docs/phase-08/hands-on.md)
- [Verification and limits](docs/phase-08/verification.md)
- [Change summary](docs/phase-08/summary.md)
- [Phase 9 handoff: the full drafting and results interface](docs/phase-09-handoff.md)

Earlier guides remain in `README-phase1.md` through `README-phase7.md`. The original game still runs independently with its legacy rules and simulator.
