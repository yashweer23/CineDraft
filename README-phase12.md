# CineDraft — Phase 12: gameplay analytics and business intelligence

**Where do drafts stop, and what evidence supports the answer?** This cumulative VS Code project adds an offline analytics dashboard, private gameplay-event downloads, and an explicit practice replay. It includes every previous phase and your startup fixes. Packaged 3 November 2026.

**Start here:** extract `CineDraft-VSCode/`, open it in VS Code, then open [the bundled synthetic dashboard](docs/phase-12/demo-dashboard.html) in a browser. It works directly from disk without Docker, a database, a TMDB key, or an internet connection. No website is deployed. If you downloaded this README separately, place it at the project root for its relative links.

In the invented sample, **7 of 12 drafts released (58.3%)**. Three were explicitly abandoned after two picks; two were still unfinished. Expand **Inspect all 12 trace rows** to see which seven start events have an official release. These are reproducible teaching data, not observations of real users.

## 1. Rebuild the demo yourself

Use Python 3.12. In PowerShell, from the extracted project root:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location backend
.\.venv\Scripts\python.exe -m scripts.gameplay_analytics demo --out ../analytics-output/demo
Pop-Location
Start-Process .\analytics-output\demo\dashboard.html
```

Reuse your existing backend virtual environment if already installed. In VS Code, **Terminal → Run Task → CineDraft: Build Phase 12 synthetic BI dashboard** runs the same exercise using `backend/.venv`.

The command creates `gameplay.sqlite`, `metrics.json`, and `dashboard.html`. Run it again: the session count stays 12. To verify the completion rate independently, run this standard-library script from the root:

```powershell
.\backend\.venv\Scripts\python.exe .\docs\phase-12\audit_demo.py .\analytics-output\demo\gameplay.sqlite
```

Expect **`7 releases / 12 starts = 58.3%`**. The output shows a start evidence key and optional release evidence key for each session. Open [the underlying audit query](docs/phase-12/audit-demo.sql) and compare it with [the dashboard SQL](backend/app/analytics/sql/metrics.sql).

For a filtered view, from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.gameplay_analytics report --db ../analytics-output/demo/gameplay.sqlite --cohort demo --genre thriller --as-of 2026-11-01 --out ../analytics-output/thriller
```

Expect **3 releases / 6 starts**. Open the new output directory's `dashboard.html`. A report needs one cohort and supports `--from`, `--until`, `--as-of`, `--genre`, `--tier`, `--catalog`, `--rules`, `--scoring`, `--simulation`, `--fixture yes|no`, and `--mode practice|closed_challenge`. Date-only inputs are midnight UTC; start windows are `[from, until)`. See [metric definitions](docs/phase-12/metrics.md) before comparing groups.

**Docker alternative:** after rebuilding the API image in section 2, from the root:

```powershell
$biDir = (New-Item -ItemType Directory -Force .\analytics-output).FullName
docker compose run --rm --no-deps --volume "${biDir}:/work" api python -m scripts.gameplay_analytics demo --out /work/demo
Start-Process .\analytics-output\demo\dashboard.html
```

The bind mount keeps the generated dashboard and SQLite file on your computer after the container exits. The running PostgreSQL service is not needed for the demo.

## 2. Upgrade your existing game

Back up local edits and the PostgreSQL volume. Merge the ZIP’s `CineDraft-VSCode/` contents into your project. Preserve your private root, backend and frontend `.env` files and TMDB credentials. The ZIP includes environment examples, not secrets.

| Service | Your address | Setting |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `WEB_PORT=5174` |
| API documentation | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native `backend/.env` `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Existing prototype service |

The native frontend uses `API_PROXY_TARGET=http://127.0.0.1:8001`. Docker keeps `api:8000`, `db:5432`, and internal frontend port `5173`. Setup preserves existing environment files; if installing fresh, set the generated ports to your values above. Keep the existing Compose project name and volume. Do not run `docker compose down -v` to upgrade.

From a PowerShell terminal at the project root, with Docker Desktop running Linux containers:

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

Expected: **`0008_phase12`**, **42 application tables**, API **`0.12.0`**. This adds one PostgreSQL table, `draft_replays`, to link deliberate practice replays. Ordinary analytics events are projected from receipts already saved by the game. There is no analytics background job, upstream request, new service, or talent catalog rebuild. The SQLite file is a separate local analysis copy and is never used as the gameplay database.

Rollback below Phase 12 refuses to erase saved replay links. Prefer keeping the schema while fixing code, or restore a pre-upgrade backup into an isolated database. Prior immutable history guards remain intact.

For native frontend and API editing, use [Phase 11’s native setup](README-phase11.md#7-edit-and-run-natively). Use **Node 24.15+ within 24.x** for the frontend, **Python 3.12** for the backend, and your PostgreSQL 17 stack. Run `alembic upgrade head` with this Phase 12 source.

## 3. Analyze your own playtest

1. Sign in or restore your guest session. Open a film, then expand **Gameplay analytics & practice replay** below the roster. Started, unfinished, abandoned, and released practice films can all be exported. An open challenge stays embargoed until it closes.
2. Choose **Download my gameplay events**. The owner-authorized JSON includes stable evidence IDs, selected slots, selectable offers, fees, and official outcomes when available. It omits usernames, bearer tokens, seeds, original draft UUIDs, raw request bodies, and comparison outcomes. An export still reveals private casting choices; keep it local unless the owner chooses to provide it for a playtest.
3. Place the download in `analytics-output/` and rename it `my-film.json` for the example below. From `backend/`, import it into your local analytics database:

```powershell
.\.venv\Scripts\python.exe -m scripts.gameplay_analytics import ../analytics-output/my-film.json --db ../analytics-output/my-study.sqlite --cohort internal
.\.venv\Scripts\python.exe -m scripts.gameplay_analytics report --db ../analytics-output/my-study.sqlite --cohort internal --out ../analytics-output/internal-report
```

Default to `internal` for development and test activity. For a **different film played by an observed human participant**, import its owner-provided export using `--cohort playtest --observed-human`, then run `report --cohort playtest`. The catalog’s source and the activity’s source are separate: a human can play a fixture catalog; automated testing on a TMDB catalog is still internal activity. Import cannot relabel an existing session. Generated demo streams cannot enter either live cohort. Files are local evidence, not signed attestations.

4. Finish a partly captured film, download it again and reimport the newer snapshot into the same database/cohort. Only previously unseen events and eligible offers are added. Reimporting identical evidence adds zero. An older snapshot or altered historical event is rejected with the previous data preserved.
5. Open `dashboard.html` in the selected report directory. Explore the completion funnel, last observed round, median round times, talent choices, genre popularity and final budget allocation. The HTML is a saved report: rerun `report` after new imports or to change filters. More exercises: [hands-on workbook](docs/phase-12/hands-on.md).

To try a replay, open a released film, choose **Replay this brief**, then confirm **Start practice replay**. This creates a new practice film with the same genre, tier and catalog and a fresh seed. It leaves the original result and challenge submission unchanged. A new seed can still yield the same offers in a small catalog. After an interrupted response, use **Retry same request**. Export the *new* film to count a `replay_start`; opening an old film or retrying a request does not count as a replay.

## 4. What the dashboard answers

| Question | Metric and denominator |
|---|---|
| How many drafts release? | Distinct official releases / starts in the selected cohort. One session means one film, not one player. |
| Where do drafts stop? | Cumulative distinct starts reaching each of eight picks, finalization and release. Unfinished films are separate from explicit abandons. |
| Which round takes longest? | Median elapsed time from start or previous initial pick to this committed pick. Shows sample count; includes idle time and rerolls. |
| Who is selected when available? | Initial selections / selectable initial offers issued for the same person and slot. Blocked cards and recast previews are excluded from this denominator. |
| How did a casting choice perform? | Official final-roster film count, mean studio score and mean fictional profit. Associations are descriptive; hypothetical results never enter these figures. |
| Where did the budget go? | Final fees by slot, reserve, unused hiring allowance and fee utilization over released films. Recasts replace earlier fees. |
| Can I audit a number? | Each completion trace pairs a start event with its official release event, if present. Full keys match the local event table and owner export. |

The demo’s co-lead median is **88.5 seconds across 8 observed picks**. The three films abandoned before that pick contribute to the funnel but cannot contribute a measured co-lead completion time. See the [decision memo](docs/phase-12/decision-memo.md) for a testable interface idea and its limitations.

## 5. Run checks

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

The second `api-tests` command runs the actual PostgreSQL integration suite in isolated schemas on your development database. Native equivalent from `backend/`: `.\.venv\Scripts\python.exe -m scripts.run_integration`.

Optional browser exercise with invented HTTP responses:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
$env:CINEDRAFT_E2E_START = '1'
npm run test:browser:phase12
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

**Observed:** 369 backend tests, 55 frontend tests and 4 original-game tests passed. The frontend built successfully. Two browser journeys verified the file download, replay retry, embargo and offline trace at desktop and mobile widths with mock HTTP. The **102 PostgreSQL tests were skipped here**. Docker, Windows execution, and browser → live API → PostgreSQL checks remain local verification steps. See [the full verification record](docs/phase-12/verification.md).

## 6. Files worth opening in VS Code

| File | What to learn |
|---|---|
| [Source projection and replay](backend/app/analytics/service.py) | How immutable game receipts become private events |
| [SQLite import and reporting](backend/app/analytics/mart.py) | Deduplication, conflicting snapshots, cohort boundaries, time filters |
| [Metric queries](backend/app/analytics/sql/metrics.sql) | Funnel, median, choice rate, budget allocation and evidence trace |
| [Demo generator](backend/app/analytics/demo.py) | How the twelve invented sessions were constructed |
| [Dashboard renderer](backend/app/analytics/dashboard.py) | Portable HTML with escaped catalog text and no remote assets |
| [Studio controls](frontend/src/AnalyticsTools.tsx) | Owner export and explicit replay confirmation |
| [API / recovery](docs/phase-12/api.md) | Endpoint contracts, state transitions and retry rules |
| [Phase 11 README](README-phase11.md) | Accounts, earlier phase guides, simulation, what-if and native setup |

**Next: [Phase 13 — correctness, balance and performance validation](docs/phase-13-handoff.md).**
