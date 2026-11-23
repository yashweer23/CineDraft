# Phase 13 — verification record

Build reviewed 5 November 2026. Source: the cumulative Phase 12 ZIP, SHA-256 `dbe6caa7bd0ab427c90d4bbddbc5c45438c881c09b479f803ffdbf4559ad26ce`. Phase 13 keeps the existing database migration head and rule/simulation versions.

## Executed here

| Check | Observed result | Scope |
|---|---|---|
| Backend `python -m pytest -q` | **571 passed; 104 skipped** | Real pure-engine, FastAPI test-client and analytics tests; PostgreSQL skips explicitly reported |
| Frontend `npm run test:frontend` | **55 passed** in 9 files | React/component/API-state regressions |
| Frontend `npm run build:frontend` | Passed | TypeScript validation and Vite production build |
| Original game `npm test` | **4 passed** | Includes 540 generated legacy drafts; separate from the Phase 13 1,800 |
| `npm run test:browser:all` | **4 suites / 8 journeys passed** | Chromium at 1280 and 390 px; mocked HTTP; actual UI and local downloads |
| Synthetic balance experiment | **1,800 complete drafts** | 10 genres × 3 tiers × 20 seeds × 3 strategies; every result simulated twice |
| Balance evidence audit | Matched | Raw CSV hash, required cell/seed coverage, all summaries and paired denominators reconciled |
| Solver benchmark | **2.34–3.24×** median speedup | Four pure-Python synthetic workloads, same exact output witnesses; not API latency |

The browser checks exercise complete guest drafts, restoration, recast preview/cancel, registrations, challenge attempts, release embargo, public rankings, paired what-if controls, repeated identical requests, navigation locks, owner exports and confirmed practice replay. They test interface behavior using invented responses. Database ownership, transaction isolation and actual concurrency depend on the separate PostgreSQL suite. The UI is unchanged by Phase 13; the new browser runner sequences existing regression suites.

The final backend total includes **202 added passing tests** over Phase 12, including generated cases, benchmark failure behavior and raw-report audit checks. Two additional PostgreSQL tests validate catalog inventory and a database/catalog mismatch; both remain unrun here. Existing analytics reimport/deduplication and what-if paired-recomputation tests also passed. The copied Phase 12 assignment implementation is source-hash pinned; existing exhaustive matching tests provide an independent correctness oracle.

Runtime: Python 3.12.14; Node 24.22.1; locked application dependencies; Playwright 1.51.1 with Chromium headless build 1161. The [solver report](evidence/assignment.json) includes hardware, source hashes, every timed round and separate profiling records. Timed solver measurements were run without concurrent test/browser jobs. Visible CPU count does not establish a container's actual CPU quota.

## Not executed here

| Item | Status / next action |
|---|---|
| PostgreSQL integration | **104 skipped**: no PostgreSQL server or Docker runtime in the build environment. Run the documented Docker or native integration command. |
| Live browser → API → PostgreSQL | Not run. Activate a synthetic catalog, then run the live guest journey locally. |
| HTTP load/performance | Not run. Use `scripts.benchmark_api` against your local API and matching database. No latency or throughput values are supplied. |
| Human playtests | **0 observed participants.** Use the blank worksheet and distinguish observations from generated sessions. |
| Windows / Docker Desktop execution | Not run here. PowerShell commands and existing port configuration are documented for local verification. |
| Production deployment / capacity | Outside this delivery. No site, hosting resource or GitHub release was created. |

[Machine-readable outstanding status](evidence/live-status.json) records these gaps. No claims about human usability, real-catalog balance, API latency or production throughput follow from the executed checks.

## Compatibility and package checks

API and package version are `0.13.0`; migration head is still `0008_phase12`, with 42 application tables. No dependency or public endpoint was added. The current OpenAPI export changes only the application/health version; historical contract schemas remain unchanged.

The cumulative package preserves the original four game assets, Compose and environment examples, environment setup/connection scripts, test Dockerfile, Alembic configuration, persistence savepoint fixture, all eight migrations, scoring/rules configuration, simulation and what-if engines. Phase 12's README is retained verbatim as `README-phase12.md`. Private `.env` files, dependencies, caches, local databases, playtest notes and browser screenshots are excluded. Packaged synthetic evidence remains under `docs/phase-13/evidence/`.

The ZIP contains a sorted `MANIFEST.sha256`. Packaging verifies each entry's hash, unique names, ZIP integrity, valid JSON/Python syntax and local Markdown link targets. The standalone README is an exact copy of the root README.
