# CineDraft — Phase 10

**Accounts, daily challenges and server-scored leaderboards.** This cumulative VS Code project adds account ownership to the Phase 9 studio and a separate official challenge flow. Updated 1 November 2026. Run it locally; no deployment is included.

You can register, sign in, claim your guest films, enter one daily attempt, release it and compare scores after the deadline. The original game, your port fixes and the existing drafting/scoring rules are preserved.

**Verification:** backend unit and frontend/browser checks passed during packaging. Real PostgreSQL integration, Docker execution and Windows execution remain local checks; run the database suite below before relying on competitive results. See [the exact verification record](docs/phase-10/verification.md).

If you downloaded this README separately, put it at the project root as `README.md` so its relative links work.

## 1. Upgrade your existing project

Back up your local edits and database first. Merge the ZIP's `CineDraft-VSCode/` contents into your project. Keep your three private `.env` files, TMDB credentials and PostgreSQL volume. The ZIP contains only environment examples.

| Service | Your address | Setting to preserve |
|---|---|---|
| Studio | [http://localhost:5174](http://localhost:5174) | Root `.env`: `WEB_PORT=5174` |
| API docs | [http://localhost:8001/api/docs](http://localhost:8001/api/docs) | Root `.env`: `API_PORT=8001` |
| PostgreSQL | `127.0.0.1:5433` | Root `POSTGRES_PORT=5433`; native backend `DB_PORT=5433` |
| Original game | [http://localhost:5500](http://localhost:5500) | Prototype service |

Native frontend configuration stays `API_PROXY_TARGET=http://127.0.0.1:8001`. Docker uses its existing internal addresses `api:8000`, `db:5432`, and frontend port `5173`.

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

Expect **`0006_phase10`**, **39 tables**, and API version **0.10.0**. Rebuilding the API installs the timezone-data dependency; rebuilding the web image supplies the matching UI. No talent, pricing, graph or catalog rebuild is needed for an existing working catalog.

Migration 0006 adds seven tables: accounts, account sessions, ownership claims, authentication throttles, daily challenges, attempts and submissions. It extends the runtime owner guard for account ownership and adds immutable-history and competition-deadline guards. It does not rewrite old drafts, fees, snapshots, results or earlier migrations. The database savepoint/test-image fixes you supplied remain included.

Setup preserves existing environment files. For a fresh installation, set the ports in the table after generation; see [the Phase 5 environment guide](README-phase5.md#2-confirm-your-ports). Do not use `docker compose down -v` for an upgrade.

**Rollback:** once account or challenge history exists, downgrade below Phase 10 is refused. Retain the upgraded schema while fixing code, or restore a deliberate pre-upgrade backup into an isolated database. Deleting history or disabling triggers is not a recovery procedure.

## 2. Create an account and keep guest films

Open the studio and expand **Account sign-in & registration**:

1. Choose **Register**, enter a public username and a unique passphrase, then **Create account**.
2. Usernames use 3–32 letters, digits or underscores and become lowercase. Passwords use 15–128 characters, at most 512 UTF-8 bytes. Password whitespace and Unicode are preserved.
3. Use **Start draft** to make a practice film, or **Load my films** to reopen an account-owned film.
4. **Sign out** revokes this session. Refreshing the page clears the in-memory token; sign in again with your username and password. Films remain owned by your account.

Account sessions last **eight hours**. There is no automatic renewal, email delivery or OAuth setup. A new login creates a new session without moving film ownership. Guest play still works with the existing 30-day recovery token.

To move existing guest films:

1. Privately save the guest recovery token. Close the guest session on screen and sign in to the destination account.
2. Expand **Claim guest films or change password**.
3. Enter the guest token, acknowledge the ownership change, then **Claim all guest films**.
4. Choose **Load my films**.

A claim transfers **every film belonging to that guest session**. It permanently revokes guest access, including other tabs using that token. It leaves historical owner hashes, offers, receipts and frozen inputs intact. Repeating the same claim on the same account is safe; another account cannot claim it. A lost, expired or previously revoked token cannot prove ownership. Knowing a draft UUID is insufficient.

**Change password and sign out** verifies the current password and revokes all account sessions. If you forget your password, the trusted local database operator can reset it interactively:

```powershell
docker compose run --rm api python -m scripts.reset_account_password --username your_username
```

Passwords are prompted without echo and are not command-line arguments. The reset revokes every account session. It does not recover a lost guest token.

## 3. Prepare a catalog if needed

Skip this section if drafting already works. For a fresh synthetic practice catalog, no TMDB key is required:

```powershell
docker compose run --rm api python -m scripts.seed_demo
docker compose run --rm api python -m scripts.build_talent --dataset fixture:dataset-v1 --version practice-ratings-v1
docker compose run --rm api python -m scripts.build_graph --dataset fixture:dataset-v1 --version practice-graph-v1
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --dry-run
docker compose run --rm api python -m scripts.prepare_drafting --pricing pricing:practice-ratings-v1 --graph graph:practice-graph-v1 --version practice-draft-v1 --activate
```

Review tier availability first. The eight-person fixture offers little choice; it verifies plumbing rather than competition balance. For richer TMDB data, use [Phase 7's catalog instructions](README-phase7.md) and retain your existing backend TMDB credential. Never put it in frontend code.

## 4. Publish today's challenge yourself

Publishing is an explicit local operator command. It is not a public API endpoint, scheduled job or frontend action.

At the project root, choose an existing catalog, an enabled tier and a local calendar date. The default challenge timezone is **Asia/Kolkata**. The date below comes from your computer; adjust it if your computer uses a different calendar timezone.

```powershell
$challengeDate = (Get-Date).ToString('yyyy-MM-dd')
$challengeId = 'daily-drama-' + $challengeDate
$challengeCatalog = 'draft-catalog:practice-draft-v1'

docker compose run --rm api python -m scripts.publish_challenge --id $challengeId --catalog $challengeCatalog --date $challengeDate --timezone Asia/Kolkata --genre drama --tier blockbuster --dry-run
docker compose run --rm api python -m scripts.publish_challenge --id $challengeId --catalog $challengeCatalog --date $challengeDate --timezone Asia/Kolkata --genre drama --tier blockbuster
```

Replace `$challengeCatalog` with your catalog ID. `blockbuster` provides the widest fixture budget; you can choose `indie` or `studio` if the catalog enables it. IDs use lowercase letters, digits, underscores or hyphens, starting with a letter/digit, up to 80 characters.

The challenge opens at midnight in its chosen timezone and closes at the next midnight. Future dates create scheduled challenges. Already-closed dates are rejected. The CLI returns the UTC boundaries, fixed version bundle, configuration hash and seed commitment. It does not print the secret seed. Repeating an identical publication keeps its original seed; reusing the ID with a different configuration fails. Published definitions cannot be edited.

## 5. Play and compare an official attempt

1. Sign in and expand **Daily challenges & leaderboards**. Choose **Refresh challenges**.
2. Inspect the genre, budget, timezone and deadline. Device-local times are shown alongside the challenge timezone.
3. Choose **Enter challenge**, then confirm **Start my one attempt**. This consumes the account's single attempt, even if abandoned.
4. Draft eight distinct people, optionally reroll/recast, finalize and run the release **before closing**.
5. The successful release automatically creates the official submission in the same transaction. There is no manual score upload.
6. Use **Resume my attempt** or **Load my films** after signing in again.
7. After closing, choose **Refresh draft** to unlock the report and **View rankings** / **Refresh rankings** to see the final leaderboard.

The policy is **`daily-1.0`**: one attempt per account per challenge; its first successful release before the deadline counts. A failed engine run can retry the same frozen production while the challenge remains open. Abandonment or a deadline miss does not grant another attempt. Exact saved command receipts remain replayable after closing, but a new pick, recast, finalize or release cannot be backdated. Unfinished drafts can still be abandoned.

Each challenge pins a catalog, genre, budget, rules, scoring, simulation manifest and shared server-generated seed. The same actions and picks follow the same deterministic offer stream. Catalog activation later does not repin a challenge. Different challenges have separate rankings.

**Reports, the audit seed and rankings stay hidden until closing**, even from a participant who has finished. The API returns 423 for an embargoed report/seed. This prevents an early result from revealing the shared seed. After closing, **Reveal audit seed** supplies the seed for comparison with its pre-published SHA-256 commitment.

Ranking order is studio score descending, fictional profit descending, earlier submission time, then draft UUID. Username, score, profit, timestamp and output hash are public in ranking responses. Another person's draft, roster and full result remain private. Practice films never enter these rankings.

## 6. Recover interrupted work

For a draft or challenge action, use **Retry same request**. It preserves the endpoint and exact request ID/body. If the write succeeded but a following draft/roster/context read failed, use **Refresh draft** instead. A historical receipt can describe an earlier revision; the UI reloads current state before enabling another action.

For an interrupted registration, try **Sign in** with the same credentials. For an uncertain password change, try the new password, then the old password if it did not complete. Claims can safely repeat the same guest proof for the same account. Unconfirmed sign-out clears the local screen but may leave the server session valid until its eight-hour expiry.

See [account and challenge recovery](docs/phase-10/recovery.md) for cross-tab and manual request recovery. Keep a pending request ID if you need to close the tab. A different account cannot use that ID to gain ownership.

## 7. Run checks in VS Code

Use Node **24.15+ within 24.x** and Python **3.12**. At the project root:

```powershell
npm --prefix frontend ci
npm run test:frontend
npm run build:frontend
npm test

docker compose --profile verification run --rm --build api-tests python -m pytest -q -m "not integration"
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

The second Docker test command runs the actual PostgreSQL suite, including migration upgrade/downgrade and metadata comparison, account isolation, claims, throttles, attempt limits, release rollback, deadline guards, ranking pagination and concurrent requests. It uses isolated test schemas; do not point it at an unrelated production database.

Optional browser tooling is isolated from application dependencies. The packaging checks used Playwright 1.51.1 and its Chromium 134 browser with invented HTTP responses:

```powershell
npm install --prefix .browser-tools --no-save --package-lock=false playwright@1.51.1
node .browser-tools/node_modules/playwright/cli.js install chromium
$env:CINEDRAFT_WEB_URL = 'http://127.0.0.1:5184'
$env:CINEDRAFT_E2E_START = '1'
npm run test:browser
npm run test:browser:phase10
Remove-Item Env:CINEDRAFT_E2E_START
Remove-Item Env:CINEDRAFT_WEB_URL
```

These test desktop/mobile guest and account journeys. Phase 10 browser checks always use mock HTTP; run [the two-account manual exercise](docs/phase-10/hands-on.md) against your real API/database. The older `test:browser` command also supports live guest mode as documented in [Phase 9](README-phase9.md#browser-journey-checks).

For native backend editing:

```powershell
docker compose up -d db
docker compose stop api web
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
```

Keep that terminal running. In a second terminal at the project root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5174
```

Native backend commands read `backend/.env`, including `DB_PORT=5433`; the frontend reads its `API_PROXY_TARGET`. The new `tzdata` dependency supplies the fallback IANA timezone database used on Windows. CLI commands from Docker examples can run as `python -m scripts.<command>` from `backend/` with the virtual environment's Python. Native database tests use `python -m scripts.run_integration`.

## 8. Explore and extend

| Files | Hands-on purpose |
|---|---|
| `backend/app/accounts/` | Password hashing, bearer sessions, throttling and guest claims |
| `backend/app/challenges/` | Immutable challenge policy, deadline checks, official submissions and ranking reads |
| `backend/migrations/versions/0006_phase10.py` | Frozen schema and SQL guards |
| `backend/app/drafting/auth.py`, `service.py` | Shared guest/account authorization and pinned draft creation |
| `backend/app/simulation/service.py` | Atomic official submission and report embargo; engine formulas unchanged |
| `frontend/src/AccountPanel.tsx`, `ChallengePanel.tsx` | Account controls, daily entries, rankings and audit |
| `frontend/src/studioApi.ts`, `Studio.tsx` | Exact request recovery and challenge-aware studio state |
| `backend/tests/test_phase10_*.py`, `frontend/src/Phase10.test.tsx` | API, database and interaction checks |

The project remains a local learning application. A local database operator can inspect seeds and reset accounts. Users can create multiple usernames; the one-attempt rule is per account, not verified person. There is no production abuse certification, email recovery, MFA, account deletion/anonymization, public hosting or external identity provider in this phase. See [the security and competition design](docs/phase-10/design.md) for the implemented boundaries.

Further reading: [API](docs/phase-10/api.md), [hands-on exercises](docs/phase-10/hands-on.md), [verification](docs/phase-10/verification.md), and [Phase 11 handoff: the controlled What-if lab](docs/phase-11-handoff.md).

Stop Docker with `docker compose down` to retain its data volume. The standalone original game remains on port 5500.
