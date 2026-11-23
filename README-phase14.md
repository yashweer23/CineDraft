# CineDraft · Phase 14 — local portfolio release

CineDraft lets you draft a director, four actors, a writer, a cinematographer and a composer within a fictional movie budget. It uses credited work to explain why a cast fits together, then shows what changes if you replace one hire. **Phase 14 is the final core phase:** a cumulative VS Code project, a reproducible demo, and interview materials. Version **0.14.0**, packaged **6 November 2026**.

**First exercise:** extract `CineDraft-VSCode/`, open that folder in VS Code, and play [the 2:10 captioned walkthrough](docs/phase-14/worked-film.mp4). Then reproduce the same film in section 1. The demo's cheaper director saves $7.975M in fees but reduces median fictional profit by about $6.02M. You can trace that comparison back to the picks, fees and credits.

| Your goal | Start here |
|---|---|
| Reproduce a film without Docker or a key | Section 1; [worked-film evidence](docs/phase-14/worked-film.json) |
| Play the full local studio | Section 2; your usual `localhost:5174` |
| Explain the architecture | [System and ER diagrams](docs/phase-14/architecture.md) |
| Prepare an interview or recording | [Timed demo script, project bullets and Q&A](docs/phase-14/interview.md) |
| Back up, restore, or diagnose startup | [Local operations runbook](docs/phase-14/operations.md) |
| Assess readiness or build a release | Sections 3–4; [release notes and evidence ledger](docs/phase-14/release.md) |

If downloaded separately, place this README at the extracted project root so its relative links work. The ZIP contains the source, previous phase guides, docs, demo media and checks; private configuration and installed dependencies are not included.

## 1. Run the worked film in VS Code

From the root in PowerShell, using Python 3.12. Reuse your existing environment if installed:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location backend
.\.venv\Scripts\python.exe -m scripts.prepare_demo --preview
.\.venv\Scripts\python.exe -m scripts.portfolio_tour
Pop-Location
```

On macOS/Linux, use `python3.12 -m venv backend/.venv` and `.venv/bin/python` for commands inside `backend/`. After dependencies are installed, both exercises run offline. In VS Code, **Terminal → Run Task → CineDraft: Run the worked film** uses the same virtual environment.

The preview builds role ratings, top-five works, fictional fees, and collaboration edges from **36 fictional people, 20 films and 228 credits**. Two people have more than one role. The production solver finds a minimum complete roster of **$28.75M**. Indie has a $6.5M hiring allowance, so disabling that tier is correct; Studio and Blockbuster are enabled. [Reference preview](docs/phase-14/demo-preview.json).

The tour chooses legal cards from seeded offers for a Thriller/Blockbuster brief. It commits **$62M** to hires, combines them with the **$70M** reserve, and obtains a **53/100** studio score and **$41,133,791** fictional profit. It compares another director across 64 paired scenarios and checks the original result hash again. This is an offline exercise using production calculations and an in-memory snapshot, not a saved API film. A live studio game uses a fresh seed and will usually be different.

**Try it:** from `backend/`, run `.\.venv\Scripts\python.exe -m scripts.portfolio_tour --json`. Find the `evidence` object: *Synthetic Thriller Study 19* credits Actor 12 and Director 06. Compare `studio_receipts_usd` with `worldwide_gross_usd`, then subtract production and marketing from receipts. In `comparison`, inspect the paired P10, median and P90 differences. These are fictional scenario outcomes, not real-world financial predictions.

## 2. Run or upgrade the full studio

Use Docker Desktop with Linux containers, and Node **24.15+ within 24.x** for local frontend development. Keep your root, backend and frontend private `.env` files and the existing PostgreSQL volume. On an existing installation, take a [backup](docs/phase-14/operations.md#back-up-before-merging-or-migrating) before merging the new source. Use the same Compose project name. **Do not use `docker compose down -v` to upgrade.**

From the root run `node scripts/setup-env.cjs`. Existing files are kept. For a fresh setup, set the following after generation; the defaults are 5432/8000/5173 and changing the root file alone does not rewrite the two native files:

| Service | Your address | Configuration |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `API_PORT=8001` |
| PostgreSQL 17 | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native `backend/.env`: `DB_HOST=127.0.0.1`, `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Existing prototype service |

In `frontend/.env`, use `API_PROXY_TARGET=http://127.0.0.1:8001`. Keep the native backend CORS origins aligned with `localhost:5174` and `127.0.0.1:5174` if making cross-origin calls. Docker uses `api:8000`, `db:5432`, and internal frontend port `5173`. Your originals, configurable-port setup, test-image contract files and database isolation fixes are preserved.

```powershell
docker info
docker compose build api web
docker compose up -d db
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose up -d api web prototype
npm run check:stack
```

Expect `0008_phase12`, **42 application tables**, API `0.14.0`. No migration or catalog rebuild is needed when moving from Phase 13. Earlier phases' historical migrations and frozen simulation rules remain unchanged.

**If you already have a catalog you want to keep active**, open the studio and use it as usual. To add the new demo without changing the active catalog, run `docker compose run --rm api python -m scripts.prepare_demo`. To make the fictional portfolio catalog the default for future drafts, run:

```powershell
docker compose run --rm api python -m scripts.prepare_demo --activate
```

This explicitly activates `draft-catalog:portfolio-v1`. The builder reuses matching sealed versions on rerun and refuses conflicting data. Dataset, talent/prices, graph and catalog publish in separate transactions; retry after a failed stage to resume. Existing drafts retain their pinned catalogs and results. To switch back later, use the original catalog's pricing ID, graph ID and original label with `scripts.prepare_drafting --activate` as described in [Phase 7](README-phase7.md). Record those values before switching if you need to restore the default.

Open the studio, create or restore a guest session, privately save the recovery token, choose **Thriller → Blockbuster**, and draft eight people. Open a dossier, inspect the listed works and shared credits, then review and finalize. Run the release, open **Why this score?**, and use the **what-if lab** to compare an affordable substitution. The [demo script](docs/phase-14/interview.md) explains what to show and why. No TMDB credential is needed for synthetic practice. For real data, keep the long TMDB API Read Access Token in `backend/.env` only; see [the import guide](README-phase5.md#4-choose-or-import-a-dataset).

## 3. Verify on your machine

From the root:

```powershell
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test
npm run test:ops
py -3.12 -m unittest discover -s tests -p test_release.py
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

The second `api-tests` invocation sets the real PostgreSQL connection and runs integration tests in isolated schemas. A plain `pytest` run with skipped cases is not evidence of a database pass. For native execution, use `.\.venv\Scripts\python.exe -m scripts.run_integration` from `backend/` against your development database.

**Observed for this package:** 574 backend tests passed, 106 PostgreSQL cases skipped; 55 frontend and 4 original-game checks passed; TypeScript/Vite build passed; 8 mocked browser journeys passed; 8 package checks and 3 backup-wrapper tests passed. The wrapper tests simulate `pg_dump` output, not an actual database restore.

Use [Phase 13 browser instructions](README-phase13.md#4-run-regression-checks) for the optional Playwright install and the live synthetic guest journey. Use [Phase 13's live HTTP benchmark](README-phase13.md#5-measure-your-live-api) and [playtest worksheet](docs/phase-13/playtest.md) for measured latency and actual player feedback. Remaining live PostgreSQL, Docker backup/restore, Windows, independent clean-install, hosted CI and observed playtest checks are listed in the [evidence ledger](docs/phase-14/release.md). The earlier 1,800-run strategy evidence and solver timings remain bundled with their original scope.

## 4. Build your own source ZIP

Python standard library only. From the root:

```powershell
py -3.12 scripts/package_release.py build --out release-output/CineDraft-v0.14.0.zip
py -3.12 scripts/package_release.py verify release-output/CineDraft-v0.14.0.zip
```

Expect `verified: true`, a file count and whole-archive SHA-256. The tool packages only reviewed paths in [release-files.txt](release-files.txt), pins ZIP timestamps/permissions, and computes a fresh per-file manifest inside the ZIP. It refuses symlinks, private/generated paths, nonmatching hashes and existing output names. Use a new output name for a second build; identical source bytes and the same Python/compression runtime yield the same ZIP hash. For the delivered ZIP, verify it by passing its actual downloaded path instead.

The release is prepared for a repository, but no GitHub project, remote tag or hosted site was created. Follow [the release checklist](docs/phase-14/release.md#turn-the-local-package-into-a-reviewed-release) when you choose a repository. For an interview, start with the casting decision in section 1 and the [source-backed project bullets](docs/phase-14/interview.md), then show the code that supports your claims.

**What comes next:** finish the live checks and record your own studio demo. The original roadmap has **14 core phases**. [Phase 15 — real-time multiplayer draft rooms](docs/CineDraft_Development_Roadmap.md#phase-15--real-time-multiplayer-draft-rooms) is an optional extension.
