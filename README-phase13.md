# CineDraft — Phase 13: correctness, balance and performance

**Run the experiments yourself in VS Code.** This cumulative ZIP adds generated-draft checks, a paired strategy study, an exact roster-solver optimization, a local API benchmark, and a human playtest worksheet. It includes all previous phases and your startup fixes. Packaged 5 November 2026; nothing is deployed.

**Start here:** extract `CineDraft-VSCode/`, open that folder in VS Code, and run section 1. No TMDB key, Docker, or database is needed for the balance and solver experiments. If this README was downloaded separately, place it at the project root so its links resolve.

Observed in this build: **1,800 synthetic drafts**, **571 passing backend tests**, **55 frontend tests**, **4 original-game tests**, and **8 browser journeys with mocked HTTP**. The **104 PostgreSQL integration tests were skipped here**. Live API measurements and human playtests remain local follow-up work; see [the verification record](docs/phase-13/verification.md).

## 1. Reproduce the strategy experiment

Use Python 3.12. From the project root in PowerShell:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location backend
.\.venv\Scripts\python.exe -m scripts.validate_balance --seeds 20 --out ../validation-output/balance
.\.venv\Scripts\python.exe -m scripts.audit_balance ../validation-output/balance
Pop-Location
```

Reuse your existing virtual environment if already installed. On macOS/Linux, create it with `python3.12 -m venv backend/.venv` and use `backend/.venv/bin/python` (or `.venv/bin/python` when inside `backend/`). All experiment commands below run from `backend/` unless otherwise stated.

Expect `runs: 1800`, `synthetic: true`, and audit `matched: true`. The fixed 20-seed corpus hash is:

```text
2eaf45cc2f8ad12e8b109c1109eacefb1136339611fac716741a3c55ea8822c2
```

Open `validation-output/balance/runs.csv` and `report.json` in VS Code. The first file has one row per completed film; the second contains cell statistics, paired differences, method and runtime metadata. The bundled originals are [runs.csv](docs/phase-13/evidence/balance/runs.csv) and [report.json](docs/phase-13/evidence/balance/report.json). Timing metadata will differ on your machine; deterministic run hashes should not.

There are ten genres × three tiers × twenty seeds × three strategies. All strategies see the same starting catalog and seed, and choose only from legal cards offered by the production code. `random` uses a deterministic random ranking; `genre_greedy` prefers genre fit; `star_heavy` prefers popularity. No strategy uses rerolls or recasts. Every completed result is validated and simulated twice to check exact replay.

The 84 identities, 100 person-role profiles, ratings and shared films are **invented engineering inputs**. Fictional fees use the actual pricing formula. These are not observations of players, a TMDB sample, or claims about real actors. Read [the complete methods and limits](docs/phase-13/methods.md).

| Tier | Strategy | Films | Mean unrounded studio score | Mean fictional ROI |
|---|---|---:|---:|---:|
| Indie | Random | 200 | 40.60 | −29.54% |
| Indie | Genre-greedy | 200 | 44.75 | −24.68% |
| Indie | Star-heavy | 200 | 39.00 | −31.28% |
| Studio | Random | 200 | 46.68 | −12.25% |
| Studio | Genre-greedy | 200 | 54.60 | −2.95% |
| Studio | Star-heavy | 200 | 44.35 | −11.60% |
| Blockbuster | Random | 200 | 51.87 | −1.23% |
| Blockbuster | Genre-greedy | 200 | 61.84 | 11.65% |
| Blockbuster | Star-heavy | 200 | 54.86 | 17.65% |

Genre-greedy beat random on unrounded score in **554 of 600 pairs**, tied once, and lost 45. Star-heavy won **282 of 600**, with no ties. In the blockbuster cells, star-heavy had higher mean ROI than genre-greedy despite lower mean score. Popularity does not dominate every objective in this sample. This fixed synthetic catalog cannot establish that real imported catalogs are balanced, or that any strategy is optimal. No scoring weights or prices were tuned.

For a deeper exercise, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_balance ../docs/phase-13/evidence/balance --replay
.\.venv\Scripts\python.exe -m scripts.validate_balance --seeds 50 --out ../validation-output/balance-50
```

`--replay` rebuilds all 1,800 bundled drafts and compares every CSV field. More seeds test this same catalog more extensively; they do not create more representative source data. In VS Code, **Terminal → Run Task → CineDraft: Run Phase 13 balance experiment** runs the default study.

## 2. Measure the solver optimization

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_assignment --rounds 7 --iterations 20 --out ../validation-output/assignment.json
```

Phase 13 precomputes eligible slot roles and bit masks before the solver's inner loop. The previous algorithm is preserved as an exact, hash-pinned benchmark reference. Costs, chosen identities, tie-breaking and offer legality must remain unchanged.

Observed median milliseconds per solve on Python 3.12.14, Linux x86-64, Intel Xeon Platinum 8573C, 9 visible logical CPUs:

| Workload | Person-role rows | Phase 12 | Phase 13 | Speedup |
|---|---:|---:|---:|---:|
| 30 people, 8 remaining slots | 100 | 8.092 ms | 2.955 ms | 2.74× |
| 100 people, 8 remaining slots | 333 | 12.256 ms | 4.483 ms | 2.73× |
| 1,000 people, 8 remaining slots | 3,333 | 20.304 ms | 6.268 ms | 3.24× |
| 100 people, 4 remaining slots | 333 | 0.326 ms | 0.139 ms | 2.34× |

[Raw round timings, profiles and source hashes](docs/phase-13/evidence/assignment.json) are included. The benchmark alternates function order after warmup. Container quotas and competing work affect timing. These are **pure Python solver measurements**, not HTTP latency or database throughput. There is no machine-dependent speed assertion in the tests.

## 3. Upgrade your existing local game

Back up your local edits and PostgreSQL volume. Merge the ZIP's contents into your existing project. Keep your private root, backend and frontend `.env` files, TMDB credentials, Compose project name and database volume. The ZIP includes environment examples only.

| Service | Your address | Setting to keep |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native backend `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Existing prototype service |

The native frontend keeps `API_PROXY_TARGET=http://127.0.0.1:8001`. Docker uses internal `api:8000`, `db:5432`, and frontend port `5173`. Setup preserves existing environment files; change generated defaults to the values above for a new installation. Never use `docker compose down -v` to upgrade.

From the project root, with Docker Desktop using Linux containers:

```powershell
node scripts/setup-env.cjs
docker info
docker compose build api web
docker compose up -d db
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose up -d api web prototype
npm run check:stack
```

Expected: API **`0.13.0`**, migration **`0008_phase12`**, **42 application tables**. **No new migration, dependency, catalog rebuild or scoring-version change.** Existing frozen inputs/results and historical migrations are preserved. If you need a fresh playable fixture, follow [Phase 9's practice catalog setup](README-phase9.md#3-prepare-a-practice-catalog-if-needed); its small catalog is separate from the larger offline Phase 13 experiment.

For native editing use [Phase 11's native setup](README-phase11.md#7-edit-and-run-natively), Node **24.15+ within 24.x**, Python **3.12**, and PostgreSQL **17**. The API and TMDB integration were already implemented in earlier phases. A TMDB read access token remains a private backend setting; the new validation tools need no TMDB key and make no upstream requests.

## 4. Run regression checks

From the root:

```powershell
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

The second Docker test command runs the **104 real PostgreSQL integration tests** in isolated schemas. Keep the database running. Native alternatives from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
.\.venv\Scripts\python.exe -m scripts.run_integration
```

Do not count a plain `pytest` run with skipped integration tests as a PostgreSQL pass. The expanded checks cover exact assignment witnesses, zero-fee/tied/depleted pools, multi-role uniqueness, all genre/tier/strategy combinations, money reconciliation, input-order invariance, paired zero controls, report audit failures, and benchmark error classification. Earlier authorization, idempotency, what-if pairing and analytics-deduplication regressions remain included.

Run all four browser suites from the root with their invented HTTP responses:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
$env:CINEDRAFT_E2E_START = '1'
npm run test:browser:all
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

Each suite runs at **1280 px and 390 px**. They cover guest drafts, restore/resume, recast cancellation, account/challenge flows, release embargo, paired what-if controls, exact retries, analytics downloads and practice replay. The runner starts and stops its own Vite process. Browser tools are optional local dependencies; they are not added to the application lockfile.

For the separate **live guest journey**, start the real API, activate a synthetic practice catalog, and keep native `frontend/.env` pointing to port 8001. From the root:

```powershell
$env:CINEDRAFT_E2E_LIVE = '1'
$env:CINEDRAFT_E2E_START = '1'
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
npm run test:browser
Remove-Item Env:CINEDRAFT_E2E_LIVE
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

This creates two synthetic guest films in your local PostgreSQL database. The combined mock suite refuses live mode; it cannot certify live account/challenge/analytics behavior. Recast confirmation and database races are also covered in service integration tests, not claimed as completed browser actions by the cancel-only guest journey.

## 5. Measure your live API

The API benchmark needs the running API and **the same PostgreSQL database in native `backend/.env`**. It performs read requests and a read-only database inventory; it does not create films or change results. Close other experiments for a useful comparison. Use a development database, keep the catalog fixed, and record API/DB hardware, container CPU/memory allocation, API worker count and reload setting.

From `backend/`, replace the description with your actual setup:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_api --base http://127.0.0.1:8001 --requests 240 --concurrency 1 --server-description "Your CPU; Docker resources; PostgreSQL 17; API workers 1; reload on" --out ../validation-output/api-public-c1.json
.\.venv\Scripts\python.exe -m scripts.benchmark_api --base http://127.0.0.1:8001 --requests 240 --concurrency 4 --server-description "Your CPU; Docker resources; PostgreSQL 17; API workers 1; reload on" --out ../validation-output/api-public-c4.json
```

The four public routes are readiness, catalog, people and movies. For a broader owner-read mix, finish a practice film in the studio, copy its draft UUID from the saved-film/API data, and run:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_api --draft YOUR-RELEASED-DRAFT-UUID --requests 240 --concurrency 4 --server-description "Your actual API and database configuration" --out ../validation-output/api-owner-c4.json
```

Replace the UUID placeholder. Enter your recovery/account token at the hidden prompt. The owner profile adds draft, roster, saved result and gameplay-event reads. An unfinished, unauthorized or embargoed film fails warmup. The report omits tokens and owner payloads. For automation, `CINEDRAFT_BENCHMARK_TOKEN` can supply the token; keep it private and clear it afterward.

Reports include PostgreSQL version/migration, catalog hash, dataset size, measured request counts by route, concurrency, warmup, successful and all-request p50/p95, requests/second, errors and error rate. Failures produce a nonzero exit code. Warmup/configuration failure writes no new report, so check the report timestamp before using an existing output file. [Methods](docs/phase-13/methods.md#http-load-tool) explain timing and dataset matching.

No API latency numbers have been invented or inferred from the solver benchmark. Record your results before making a throughput claim. The workload measures reads at a bounded concurrency, not maximum production capacity.

## 6. Collect real feedback and keep an evidence trail

Use the [human playtest worksheet](docs/phase-13/playtest.md) and [blank CSV](docs/phase-13/playtest-template.csv). No human sessions were observed in this build. Record actual task completion, confusion and assistance; then fix and retest an observed issue. Use [Phase 12's analytics instructions](README-phase12.md#3-analyze-your-own-playtest) to import participant-provided exports into the correct cohort. Synthetic or automated sessions stay separate.

Useful code to inspect:

| File | Exercise |
|---|---|
| [Exact roster solver](backend/app/drafting/assignment.py) | Find what moved out of the inner loop |
| [Generated corpus](backend/app/validation/corpus.py) | Trace a legal offer, selected person and frozen snapshot |
| [Balance study](backend/scripts/validate_balance.py) | Compare per-cell variability and within-seed differences |
| [Evidence audit](backend/scripts/audit_balance.py) | Change a copied CSV cell and observe rejection |
| [Solver benchmark](backend/scripts/benchmark_assignment.py) | Inspect alternating rounds and source hashes |
| [Local API benchmark](backend/scripts/benchmark_api.py) | Run the same route mix at two concurrency settings |
| [Generated regressions](backend/tests/test_phase13_validation.py) | Inspect uniqueness, accounting and exact zero controls |

**Next: [Phase 14 — local release packaging, demo and interview materials](docs/phase-14-handoff.md).** Carry the outstanding PostgreSQL, live performance and human-playtest checks into that handoff; do not mark them as completed merely because the tools are included.
