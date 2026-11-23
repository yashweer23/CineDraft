# CineDraft — Phase 9

**The guided studio: film brief → draft room → review/recast → premiere → saved release report.** This cumulative VS Code ZIP builds on Phase 8 and preserves the original game, your port fixes, guest-owned drafts, immutable snapshots and scoring rules. Updated 28 October 2026.

The new studio is the main interface. The earlier connection checks, talent lab, collaboration lab and draft inspector remain under **Developer tools**. This is a local project to run and explore in VS Code; nothing is deployed.

If you downloaded this README separately, place it at the project root as `README.md` so its relative links work.

## 1. Upgrade your existing folder

Back up your local edits, then merge the ZIP's `CineDraft-VSCode/` contents into your project. Keep your root, backend and frontend private `.env` files, TMDB credentials and database volume. The ZIP contains examples, not private environment files.

| Service | Your address | Configuration to keep |
|---|---|---|
| Guided studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API documentation | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native backend `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Original prototype service |

For native frontend development keep `API_PROXY_TARGET=http://127.0.0.1:8001` in `frontend/.env`. Docker still uses internal `api:8000`, `db:5432` and web port `5173`.

Run in PowerShell at the project root, using Docker Desktop's Linux containers:

```powershell
node scripts/setup-env.cjs
docker info
docker compose up --build -d
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
npm run check:stack
```

**The migration head remains `0005_phase8` (32 tables). No Phase 9 migration is added.** The API version becomes **0.9.0**. Rebuild both images so the new frontend and roster endpoint are available together. No talent, pricing, graph or draft catalog rebuild is required for an existing Phase 7/8 installation.

Setup preserves existing `.env` files. A fresh installation uses example defaults; change those to your ports above. See [Phase 5 setup](README-phase5.md#2-confirm-your-ports) for the original environment instructions. Do not use `docker compose down -v` to upgrade.

## 2. Open your studio

Open [http://localhost:5174](http://localhost:5174).

For an existing film:

1. Enter its recovery token under **Returning to a production?** and choose **Restore session**.
2. Expand **Session & saved films**, then open the saved film.
3. Continue its exact saved offer, finish a review, or reopen an existing release report. The new roster endpoint restores names and films from the original saved offers.

For a new film:

1. Choose **Create guest session**.
2. Expand **Session & saved films**. Reveal and privately save your recovery token, then hide it again.
3. Choose one of the ten genres and an available production budget.
4. Check **I saved my recovery token privately**, then choose **Start draft**.

The token stays in memory only. Refreshing clears it from the page, but does not delete your films. Restore it manually to continue. The existing 30-day expiry is not extended by restoring; expired, revoked or lost tokens cannot be recovered in this phase. A new token does not inherit an old token's films.

If the catalog is unavailable, the studio shows the real setup error. It does not silently substitute a practice game.

## 3. Prepare a practice catalog if needed

Skip this section when your existing drafting catalog already works. For a fresh synthetic catalog without a TMDB key:

```powershell
docker compose run --rm api python -m scripts.seed_demo
docker compose run --rm api python -m scripts.build_talent --dataset fixture:dataset-v1 --version practice-ratings-v1
docker compose run --rm api python -m scripts.build_graph --dataset fixture:dataset-v1 --version practice-graph-v1
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --dry-run
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --activate
```

Review the dry-run tier availability before activation. The small fixture has only eight people, so offers can be short and recast alternatives can be empty. The UI labels all fixture data **Synthetic practice**. For real imported data use the [Phase 7 catalog guide](README-phase7.md).

Activation changes the catalog for future drafts. Existing drafts retain their original version bundle.

## 4. Draft, inspect and recast

The draft room keeps four figures visible: hiring money remaining, locked talent spend, non-talent production reserve and actual production commitment. The roster lists all eight slots and fills in names and locked fees after each saved pick.

Each candidate shows a fictional price, game talent strength, genre fit, coverage, specialties and up to five visible role-specific films. Missing images use neutral placeholders; missing facts are not invented. Initials identify talent because existing saved offer cards do not include portrait URLs.

- **View a dossier:** inspect the pinned catalog's full eligible role-specific filmography, page through it, read attribute evidence and research shared credits with current picks. This is the imported catalog, not a claim of complete career coverage. Research counts are distinct from the twelve relationships used in scoring.
- **Select a person:** inspect the confirmation summary and projected hiring balance. Only **Confirm selection** commits. Disabled cards explain why the server blocked them.
- **Reroll:** changes the current offer using one of your two server-controlled rerolls. A small catalog may have no different valid offer.
- **Review:** after eight picks, inspect the named roster and fees. Preview one optional replacement. The original person and budget stay in place during the preview.
- **Recast:** the confirmation shows the old fee refund, new fee, net cost/refund and projected balance. Canceling preserves the original roster. Reopening a slot uses the same saved alternatives.
- **Finalize:** choose **Finalize production**, then **Lock roster**. This permanently freezes the inputs. No recast is available afterward.

The frontend displays arithmetic previews but never submits prices, eligibility, client-selected seeds or scores. The API validates every decision at the current draft revision.

## 5. Release and read the report

Choose **Run release simulation** after finalization. The saved report separates:

- Studio score and its four contributions.
- Simulated critics and audience reviews.
- Worldwide gross, studio receipts, production, marketing, total cost and profit.
- Four weekly grosses that sum exactly to the saved total.
- Twelve chemistry relationships, shared-film evidence and source coverage notes.

Marketing is additional modeled release spending. Unused hiring authorization is not charged as production. All outcomes are fictional game outputs. [Phase 8's formulas and replay instructions](README-phase8.md) still apply unchanged.

**Refresh release report** only reads. Successful films have one saved result, with no reroll control. **Draft another film** opens a new brief after confirmation and leaves the previous film saved.

## 6. Recover without repeating a new action

| Situation | What to do |
|---|---|
| POST times out, returns an unreadable response, or a 5xx leaves the outcome uncertain | Keep the tab open. Choose **Retry same request**. It preserves the exact command ID and body; other actions are paused. |
| The command is confirmed, but loading the latest draft/roster fails | Choose **Refresh draft**. The command is already acknowledged; no extra POST is needed. |
| Another tab changed the revision, or roster/draft reads disagree | Refresh the draft before choosing a new action. |
| The server confirms `simulation_failed` | Use **Retry failed simulation** after fixing the cause. This is a new command using the same frozen inputs and seed. |
| You refreshed normally | Restore the token, open the saved film and continue from the current server state. |
| You must close a tab while a request is uncertain | Save the request shown under **Keep this request for recovery**, alongside your private token. Follow [exact-request recovery](docs/phase-09/recovery.md). |

After a successful mutation or receipt replay, the studio reads the current draft and its matching-revision roster before allowing another write. An older receipt cannot replace newer state from another tab. A browser unload warning is installed while a command is uncertain; browsers may restrict when that warning is shown.

**Close this session** clears local UI state after confirmation. It does not revoke the server session, delete films or extend expiry. The developer draft inspector has its own in-memory session state and retains its earlier workflow.

## 7. Run the checks

Use Node **24.15+ within 24.x**; native backend commands use Python **3.12**.

```powershell
# At the project root
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test

docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

Observed packaging results: **262 backend unit passes, 39 frontend component passes, 4 original-game passes, successful TypeScript/Vite build**. **66 real PostgreSQL cases were skipped here** because no usable PostgreSQL runtime/test connection was available. They include two new roster persistence/ownership cases. Run them locally before treating database behavior as verified.

### Browser journey checks

Browser tooling is optional and isolated from application dependencies. The packaging run used Playwright **1.51.1** with its Chromium **134.0.6998.35** for local UI checks:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
# Test starts its own native frontend; use an unused port.
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
$env:CINEDRAFT_E2E_START = '1'
npm run test:browser
Remove-Item Env:CINEDRAFT_E2E_START
```

The default mode intercepts HTTP with invented test responses. It tests the real React UI at **1280px and 390px**, plus a **640px reflow viewport equivalent to 200% zoom at 1280px**, modal Escape/focus, lost-response replay, review/cancel, finalization, release and refresh/token restoration. Both width journeys passed during packaging. These are UI checks, not database or scoring validation. Native browser-menu zoom, screen-reader behavior and Windows execution remain manual checks.

For the same journey against your real API/database, run the full stack, activate a **synthetic practice catalog**, then:

```powershell
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5174'
$env:CINEDRAFT_E2E_LIVE = '1'
npm run test:browser
Remove-Item Env:CINEDRAFT_E2E_LIVE
```

Live mode creates its own new guest session and film for each width, leaves that history in the database and refuses a non-synthetic catalog. It does not print tokens or touch existing films. **Live mode was not run here.** Screenshots generated by either mode stay in your local `test-results/browser/` folder, excluded from the package.

For native frontend editing, stop Docker's web service before using port 5174, then:

```powershell
docker compose stop web
npm --prefix frontend run dev -- --port 5174
```

## 8. Explore the implementation

| File | Hands-on purpose |
|---|---|
| `frontend/src/Studio.tsx` | Brief, guided stages, roster, recast and confirmations |
| `frontend/src/studioApi.ts` | Memory-only ownership, request replay and current-state reconciliation |
| `frontend/src/StudioParts.tsx` | Dialogs, visible works and pinned candidate dossiers |
| `frontend/src/ReleaseInspector.tsx` | Existing saved-result renderer, reused by both interfaces |
| `backend/app/drafting/service.py` | New read-only `roster` operation; existing game mutations remain unchanged |
| `frontend/e2e/journey.mjs` | Mock or live browser journey runner |

The only new HTTP path is **`GET /api/v1/drafts/{draft_id}/roster`**, requiring the owning guest bearer token. Its named cards come from saved offers, including the selected recast offer. It does not fetch TMDB, rebuild ratings or modify history. `LiveDraft`, Phase 7 snapshot JSON and Phase 8 result JSON are unchanged.

Further reading: [design](docs/phase-09/design.md), [verification](docs/phase-09/verification.md), [recovery](docs/phase-09/recovery.md), [hands-on exercises](docs/phase-09/hands-on.md), and [Phase 10 handoff](docs/phase-10-handoff.md).

Stop the stack with `docker compose down` to retain its data volume. The original game remains independently playable on port 5500 with its original rules.
