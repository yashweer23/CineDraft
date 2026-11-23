# CineDraft — Phase 15

**Two-player cooperative draft rooms.** This cumulative VS Code project adds invitations, alternating server-controlled turns, a shared budget, persistent deadlines, automatic picks, live WebSocket updates, reconnects and exact-request retries. Updated 7 November 2026. Application version: **0.15.0**.

You and a partner build **one film together**. This is the first multiplayer mode: two seats, one roster, one hiring budget. The host chooses a brief and a 30–180 second turn length. The host picks first; each player gets four of the eight role slots. Each person can appear only once. A timeout selects the cheapest legal candidate **in the current offer**, breaking ties by person ID. The final pick automatically freezes the production; the host runs its release through the existing studio. Rooms have no rerolls or recasts.

All earlier phases are included, including the Phase 14 fictional catalog, offline worked film and video. No TMDB credential is needed for synthetic practice. The original game, solo scoring, simulation formulas, historical snapshots and your port/setup fixes remain included. **The shared room adds a database migration and a WebSocket dependency.**

Save this standalone README as `README.md` in the extracted project root if you want its relative links to open in VS Code.

## 1. Merge and configure

Extract `CineDraft-VSCode-Phase15.zip`. Open its `CineDraft-VSCode` folder in VS Code. For an upgrade, back up local edits and merge the source files; retain your existing root, backend and frontend `.env` files and PostgreSQL volume. The ZIP contains example configuration, not your private credentials. Do not replace your database with the fictional demo.

Use Docker Desktop with Linux containers and Node **24.15+ within 24.x**. Native backend development uses Python **3.12**. Commands below use PowerShell at the project root unless stated otherwise.

```powershell
node scripts/setup-env.cjs
```

Setup creates missing environment files and preserves existing files. Review these settings yourself, especially when installing into a new folder:

| Location | Settings for your machine |
|---|---|
| Root `.env` | `WEB_PORT=5174`, `API_PORT=8001`, `POSTGRES_PORT=5433` |
| `backend/.env` | `DB_HOST=127.0.0.1`, `DB_PORT=5433`; retain your database name, user and password |
| `frontend/.env` | `API_PROXY_TARGET=http://127.0.0.1:8001` |
| `backend/.env` | `CORS_ORIGINS=["http://localhost:5174","http://127.0.0.1:5174","http://localhost:4173","http://127.0.0.1:4173"]` |

**Set the CORS line even if HTTP already works through Vite.** A WebSocket sends the browser's origin, and the API now checks it explicitly. Include the exact scheme, hostname and web port you open. Do not use a wildcard. If you choose a different web port, update both `WEB_PORT` and the origin list. Existing setup files are not silently rewritten.

| Service | Address |
|---|---|
| Studio and rooms | [http://localhost:5174](http://localhost:5174) |
| API documentation | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) |
| PostgreSQL on your host | `127.0.0.1:5433` |
| Original game | [http://localhost:5500](http://localhost:5500) |

Docker still uses `db:5432`, `api:8000` and web container port `5173` internally. Port `5173` on your host remains available to CyberSentinel.

## 2. Upgrade the database and start

For an existing running installation, take a database backup first:

```powershell
node scripts/backup-db.cjs --out backups/pre-phase15-01.dump
```

The command refuses to overwrite a previous file. A fresh installation has no old database to back up. See the [restore drill](docs/phase-14/operations.md#restore-drill-into-a-new-database) for testing a backup.

```powershell
docker info
docker compose stop api web
docker compose up -d db
docker compose build api api-tests web
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m alembic current
docker compose up -d
npm run check:stack
```

Expected migration head: **`0009_phase15`**. It adds `draft_rooms` and `room_receipts`, bringing the app to **44 tables**; the Alembic version table is separate. It preserves the previous eight migrations. Downgrade refuses to delete existing room history. Do not run `docker compose down -v` to resolve an upgrade problem.

The backend now installs `websockets==17.3`; rebuild the image or reinstall `backend/requirements.txt` in your native virtual environment. The Vite proxy now forwards WebSocket upgrades. API processes run a small deadline sweep every second; overdue turns also progress when both browsers are closed. Apply the migration before starting the API.

For the richer fictional practice catalog:

```powershell
docker compose run --rm api python -m scripts.prepare_demo --activate
```

This explicitly makes `draft-catalog:portfolio-v1` the default for **new** drafts and rooms. Existing films keep their pinned catalog. Use it for the walkthrough below. The catalog enables Studio and Blockbuster; Indie is unavailable. If you want to retain a different active catalog, omit `--activate`, and use the existing catalog for rooms instead. [Phase 14](README-phase14.md) explains catalog activation and the offline demo.

## 3. Play together in two browser windows

Two windows on the same machine are enough. Each room panel keeps its own player session in memory; no second server or account registration is required.

1. In window A, open the studio and choose **Co-op rooms** in the navigation. Click **New room player**. Open **Save your private player token** and save it privately.
2. Select **Thriller**, **Blockbuster**, and **60** seconds. Click **Create co-op room**. Save the displayed room ID and invitation code. Share those two values with your partner; keep your player token private.
3. In window B, click **New room player** and privately save that different token. Enter A's room ID and invitation code; click **Join partner**. A should show that the partner has joined.
4. In A, click **Start alternating picks**. A chooses the director. B sees the roster update and chooses the lead. Continue alternating through co-lead, supporting actors, writer, cinematographer and composer.
5. Both windows show the same remaining hiring balance and selected people. Disabled cards would leave too little money to finish all eight distinct roles. The server validates legality again when committing.
6. The eighth pick displays **Your film is locked**. Save the film ID. In the main **Your studio** section, the host restores the same guest player token, loads saved films and opens that film. Run its release and inspect the score and what-if lab as in previous phases. An account host signs in to that same account instead.

The partner retains room access to the shared roster. This phase does not grant them the host's solo history, release controls or private analytics. The room shows whether the host has subsequently released the film through its draft status, but it has no shared financial report UI.

Talent exclusivity is **within this shared film**, across all eight roles. Different rooms and solo films may hire the same person. There is no competitive talent auction, matchmaking, spectator access or chat in this phase. Local addresses deliberately bind to loopback; use the two-window exercise on your machine. This package does not expose a server for friends over the internet.

## 4. Try reconnects, deadlines and retries

| Exercise | Expected behavior |
|---|---|
| Refresh window B | In Co-op rooms, paste B's token into **Existing recovery or account token**, restore, enter the saved room ID, and choose **Reopen saved room**. Reopening needs no invitation and makes no pick. |
| Close a browser during a turn | The server deadline continues. Reconnect to the saved roster and remaining turn; a disconnect does not grant extra time. |
| Create another room with a 30-second turn and let it expire | The server picks the cheapest legal offered card, labels it **Auto-picked**, and gives the next player a full turn. A browser reaching `0s` does not itself choose a person. |
| Stop the API during a turn, then restart it after the deadline | After startup, the sweep makes one overdue pick and starts a fresh full turn. It does not instantly consume all the missed turns. |
| Lose an action response | The screen blocks new commands and offers **Retry same room request**. It preserves the exact request ID and body. The server returns the saved receipt, then the client refreshes current state. |
| Two tabs using the same player submit at once | One new pick can commit. A duplicate request replays its receipt; a different request with the old revision is rejected. |
| Try the solo draft pick/reroll/recast endpoint on a room film | It returns `room_managed`. Room rules cannot be bypassed through the host's solo draft controls. |
| Host cancels before completion | Both seats see cancellation; the unfinished underlying film is abandoned. |

The countdown is based on server time supplied with snapshots. It is an estimate for display; the database clock and room lock decide whether a request arrived before the deadline. Updates are delivered roughly once a second, not a subsecond latency promise. If the WebSocket disconnects, the UI reconnects with bounded backoff and uses HTTP reads while disconnected. **Refresh room** is always available when no HTTP command is executing.

Save credentials and the room ID before closing. The server stores only the invitation hash; it cannot redisplay a lost invitation after a full refresh. A partner who already joined only needs their own session and room ID. If nobody joined and you lose the invitation, cancel that room and create another. Guest sessions expire after their existing 30-day lifetime; account sessions use their existing login/expiry rules. Reopen using the account after claiming a guest session.

If an outcome is uncertain and you must close the tab, save the JSON under **Exact request for recovery** alongside your private token. Its `path` and `body` are sufficient to submit the same HTTP POST with an Authorization bearer header. Do not invent a new request ID until that request is resolved. This is the same exact-retry pattern documented in [Phase 9 recovery](docs/phase-09/recovery.md).

## 5. Verify on your machine

```powershell
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test
npm run test:ops
py -3.12 -m unittest discover -s tests -p test_release.py
docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
```

The last command runs the real PostgreSQL suite in isolated test schemas. A plain backend pytest run that skips database tests does not establish persistence or concurrency correctness.

With the API running and the synthetic portfolio catalog activated, run the new **live two-player smoke check**:

```powershell
docker compose run --rm api python -m scripts.room_smoke --api http://api:8000 --origin http://localhost:5174
```

It creates two new test guests and one synthetic room, checks nonmember denial, joins, starts, opens a real WebSocket, alternates eight picks, tests wrong-turn/stale requests and exact receipt replay, then verifies the frozen roster and budget. It prints a JSON result without tokens. It leaves the synthetic test film in your development database and does not run its release or test timeout waiting. It refuses a non-synthetic active catalog. A failed run leaves its already-committed test state; resolve the error before rerunning. Native equivalent from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.room_smoke --api http://127.0.0.1:8001 --origin http://localhost:5174
```

Optional browser checks use Playwright isolated from application dependencies:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
$env:CINEDRAFT_E2E_START = '1'
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
npm run test:browser:all
npm run test:browser:phase15
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

The Phase 15 browser journey uses **invented HTTP and WebSocket messages** for the two-player UI; the previous four browser suites also use mocks by default. Run the smoke check and manual deadline exercise against your database before calling the full multiplayer stack verified. The browser tools are not needed to play.

**Packaging evidence and outstanding checks:** [verification ledger](docs/phase-15/verification.md). Hosted CI is configured for PostgreSQL, but no hosted run or deployment is claimed.

## 6. Hands-on code exercises

| File | Trace or experiment |
|---|---|
| [Room policy](backend/app/rooms/policy.py) | Why does `now >= deadline` reject a manual pick? Change the timeout tie-break in a copy and predict a test failure. |
| [Room service](backend/app/rooms/service.py) | Follow room lock → draft lock → legal pick → receipt. Find why replay checks precede revision checks. |
| [Deadline worker](backend/app/rooms/worker.py) | Inspect the bounded sweep and why a disconnected browser does not pause a turn. |
| [Room API](backend/app/rooms/api.py) | Find origin validation, the first-frame token and the repeated membership check. |
| [Migration](backend/migrations/versions/0009_phase15.py) | Inspect two-seat, deadline, uniqueness and receipt constraints. |
| [Room component](frontend/src/RoomLobby.tsx) | Trace a dropped acknowledgment, an old receipt and a newer WebSocket snapshot. |
| [Integration tests](backend/tests/test_rooms_integration.py) | Run the full eight-pick freeze and expired-turn cases using real PostgreSQL. |
| [Concurrency tests](backend/tests/test_rooms_concurrency.py) | Compare identical requests with two different requests racing at the same revision. |
| [Live smoke script](backend/scripts/room_smoke.py) | Replace automatic test choices with your own requests after understanding the retry rule. |

Read the [design and protocol](docs/phase-15/design.md) for transaction boundaries, the complete endpoint list, recovery semantics and limitations. Keep the historical scoring/simulation configuration immutable when experimenting; create a separately versioned ruleset for any scoring change.

## 7. Build your own ZIP

```powershell
py -3.12 scripts/package_release.py build --out release-output/CineDraft-v0.15.0.zip
py -3.12 scripts/package_release.py verify release-output/CineDraft-v0.15.0.zip
```

Add intentional new source files to `release-files.txt`. The packager rejects private environment files, backup dumps, caches and traversal paths, and refuses to overwrite an output. It verifies file hashes, not a digital signature. The older [offline demo and interview material](README-phase14.md) remain useful without a running database.

**Next checkpoint:** run the real PostgreSQL suite, the live room smoke check and a two-window timeout/reconnect playtest. Record your observations before expanding to competitive multi-film rooms or public hosting.
