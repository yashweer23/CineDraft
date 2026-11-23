# CineDraft — Phase 11

**The controlled “What if?” lab.** Swap one person in a completed film and compare the original and replacement teams across 64 paired scenarios. This cumulative VS Code ZIP includes the source, API contracts, migrations, tests and instructions from earlier phases. Packaged 3 November 2026.

The lab uses your film’s original catalog and fictional prices. It saves hypothetical reports separately; official releases and challenge rankings remain unchanged. Accounts, guest recovery, TMDB import, drafting, talent ratings, notable works, chemistry and release simulation are included.

**Verification:** 340 backend unit tests, 51 frontend tests and 4 original-game tests passed. PostgreSQL integration, Docker execution and Windows execution require your local checks. See the [verification record](docs/phase-11/verification.md). If you downloaded this README separately, place it at the project root as `README.md` for its relative links.

## 1. Upgrade in VS Code

Back up your local edits and database. Merge the ZIP’s `CineDraft-VSCode/` contents into your project, keeping your private environment files and PostgreSQL volume. No private credentials or `.env` files are included.

Your startup fixes are preserved:

| Service | Your address | Keep this setting |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native backend `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Existing prototype service |

Native `frontend/.env` stays `API_PROXY_TARGET=http://127.0.0.1:8001`. Docker retains its internal addresses `api:8000`, `db:5432`, and frontend port `5173`. Setup preserves existing environment files; on a fresh installation, change generated defaults to the ports above.

In PowerShell at the project root, with Docker Desktop running Linux containers:

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

Expect migration **`0007_phase11`**, **41 application tables**, and API version **`0.11.0`**. No new dependencies or catalog rebuild are required when your existing catalog works. The migration adds `whatif_analyses` and `whatif_receipts`, with append-only history and source/deadline guards. The original scoring engine and migrations 0001–0006 are preserved.

Keep the database test Dockerfile’s contract copy, writable pytest cache, savepoint isolation fix and Alembic path separator. These are included. Do not use `docker compose down -v` during an upgrade.

**Rollback:** downgrade below Phase 11 is refused once comparison history exists. Retain the upgraded database while fixing code, or restore a deliberate pre-upgrade backup into an isolated database. Earlier account/challenge downgrade guards remain active.

## 2. Try the lab on a completed film

1. Sign in or restore your guest session. Select **Load my films**, then open a successfully released film.
2. Below the release report, select **Open what-if lab**.
3. Choose **Role to explore**. The original person’s fee is refunded in the hypothetical budget; the replacement uses the pinned price for that role.
4. First select **Run original-person control**. Every paired change should be zero.
5. Choose an affordable replacement. Cards show talent strength, genre fit and ranked notable works. The other seven people stay fixed and distinct.
6. Read the deterministic studio-score change, hiring balance, production/marketing costs and scenario medians.
7. Expand **Scenario ranges and counts** and **Why the result changed** for P10–P90, component contributions, coverage warnings and shared-film evidence with exact credited jobs.
8. Select **Load comparison history** to reopen a saved report. Repeating the same slot/person comparison returns that same report.

A new catalog activation does not change an older film’s options. Replacements come from its full pinned role pool, including people outside the original three-card offer. Unaffordable people are shown as blocked; people occupying the other seven slots are excluded. The original person remains available through the control button even when outside the current page.

For a daily challenge, the lab becomes available **after its deadline**. Use **Refresh draft** after closing. The API enforces the embargo on candidates, history, reports and creation. Your official submission stays fixed. Guest films claimed by an account keep their comparison history under the new owner.

The original eight-person fixture may offer only the control for some roles. Use a richer existing TMDB catalog for substitutions, or run the database-free exercise below. Fresh catalog setup and TMDB import instructions remain in [Phase 10](README-phase10.md#3-prepare-a-catalog-if-needed) and [Phase 7](README-phase7.md). A legacy Phase 3 sample result is not a Phase 7 finalized film: draft and release a new film before using this lab.

## 3. A hands-on exercise without a database or TMDB key

With the rebuilt API image, run:

```powershell
docker compose run --rm --no-deps api python -m scripts.whatif_example --control
docker compose run --rm --no-deps api python -m scripts.whatif_example
```

Alternatively, from `backend/` using the Python environment described below:

```powershell
.\.venv\Scripts\python.exe -m scripts.whatif_example --control
.\.venv\Scripts\python.exe -m scripts.whatif_example
```

The control keeps the same team. The second command changes an invented director from talent strength 80 / drama fit 60 to 90 / 85 and increases the fictional fee by **$43,750**. Its deterministic studio score changes **66 → 68**. These commands make no database writes or upstream requests.

Open `backend/app/whatif/example.py` in VS Code. Change the alternative director’s attributes and matching card values together; rerun and inspect the score and paired financial changes. Keep the card’s fee and selected fee consistent. Invalid identities, roles, budgets or evidence fail validation. Do this in a learning copy; changing a published formula requires a new version rather than silently rewriting existing reports.

More exercises and expected outcomes: [hands-on guide](docs/phase-11/hands-on.md).

## 4. Understand the comparison

| Output | Meaning |
|---|---|
| Studio score | Existing deterministic Phase 8 formula, shown for both teams |
| Original / replacement median | Each team’s median across the same 64 simulated conditions |
| Paired change | Replacement minus original **within each scenario**, then summarized |
| P10–P90 | Descriptive range of the 64 simulated outcomes; not a confidence interval |
| Higher / equal / lower counts | Counts within this fixed scenario set; not real-world probabilities |
| Production cost | Original locked reserve plus hypothetical talent spend |
| Marketing | Existing Phase 8 modeled additional cost |

The baseline median is separate from your single official release. Scenario seeds derive from the original frozen input hash, sample index and `whatif-1.0`; the replacement and request ID cannot choose the seeds. Each pair shares critics, audience and revenue noise. Calculations retain Decimal precision 64 and the original financial rounding. Quantiles use linear interpolation at `(n−1) × p`.

A median paired change can differ from the difference of two medians. Higher gross alone does not imply higher profit; hiring and marketing costs also change. Ratings, prices and receipts are fictional game mechanics, not real compensation or financial forecasts. See the [design and formulas](docs/phase-11/design.md).

## 5. Recover an interrupted comparison

If the response is interrupted, use **Retry same comparison**. The UI retains the exact endpoint, request ID and body. Navigation and account actions pause until a definitive response arrives. The comparison may already be saved; do not invent a replacement request to recover an unknown outcome.

Expand **Keep comparison request for recovery** if you must close the tab. Save that JSON with your private guest recovery information, or sign in again to the same owning account. Nothing is persisted to browser storage. After reconnecting, history may already contain the report; replaying the saved body is safe. A reused request ID with different contents returns 409.

See [API and manual recovery](docs/phase-11/api.md). A new request ID for the same slot/person reuses the existing analysis; it does not create another set of scenarios. Expired sessions require reauthentication. Ownership is checked before any cached report is returned.

To verify a saved comparison, copy its analysis UUID from **Saved comparison receipt**:

```powershell
docker compose run --rm api python -m scripts.verify_whatif --analysis YOUR_ANALYSIS_UUID
```

Expect `matched: true`, `writes: 0`, and `upstream_requests: 0`. This trusted local operator command uses a read-only transaction. It recomputes the saved inputs and checks their source/result hashes. It is not a public report endpoint.

## 6. Run the checks

Use **Python 3.12** and **Node 24.15+ within 24.x**. From the project root:

```powershell
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test

docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

The second Docker test command runs real PostgreSQL tests in isolated schemas. It covers upgrades, metadata agreement, ownership, claims, pinned substitutions, exact retry, immutable history, rollback, challenge embargo and concurrent comparisons, alongside earlier phases. Run it against your dedicated CineDraft development database.

Optional browser checks use invented HTTP responses and isolated tooling:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
$env:CINEDRAFT_E2E_START = '1'
npm run test:browser
npm run test:browser:phase10
npm run test:browser:phase11
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

These exercise desktop and mobile journeys; they do not certify browser → API → database persistence. Perform the [live hands-on exercise](docs/phase-11/hands-on.md) as well.

## 7. Edit and run natively

In a VS Code PowerShell terminal at the project root:

```powershell
docker compose up -d db
docker compose stop api web
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
```

Keep that terminal running. In another terminal at the project root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5174
```

Native backend commands read `backend/.env`, including `DB_PORT=5433`. Native frontend reads `API_PROXY_TARGET=http://127.0.0.1:8001`. With the backend environment active, `python -m scripts.run_integration` runs the PostgreSQL suite. The pinned `tzdata` dependency from Phase 10 supports Windows timezone handling.

| Files | What to study |
|---|---|
| `backend/app/whatif/engine.py` | Paired scenarios, quantiles and explanations |
| `backend/app/whatif/schemas.py` | Hypothetical teams without historical offer IDs |
| `backend/app/whatif/service.py` | Pinned candidates, budgets, ownership and immutable receipts |
| `backend/app/whatif/api.py` | Four private API operations |
| `backend/migrations/versions/0007_phase11.py` | Two tables and SQL guards |
| `frontend/src/WhatIfLab.tsx` | Candidate exploration, comparison report and retry UI |
| `backend/tests/test_whatif_*.py` | Arithmetic, HTTP, persistence and concurrency checks |
| `contracts/whatif-*.phase11.schema.json` | New schemas; earlier contracts remain intact |

Accounts and daily challenges: [Phase 10 README](README-phase10.md). All earlier phase READMEs are retained. Stop with `docker compose down` to preserve the database volume.

**Next: Phase 12 — gameplay analytics and business intelligence.** See the [handoff](docs/phase-12-handoff.md).
