# Phase 12 verification — 3 November 2026

| Check | Result |
|---|---|
| Python backend, including real local SQLite queries | **369 passed; 102 PostgreSQL cases skipped** |
| Frontend component tests | **55 passed** |
| TypeScript check and Vite production build | Passed |
| Original game / local server | **4 passed**, including 540 complete synthetic drafts |
| Phase 12 Chromium journeys | **2 passed**, 1280px desktop and 390px mobile, mock HTTP; actual JSON download and offline dashboard |
| Entire migration chain, offline parser | **157 SQL statements**, including **26 PL/pgSQL function definitions**, parsed |
| Docker, native Windows, live PostgreSQL migration/ownership/concurrency | Not executed in this environment |

The 29 added backend unit cases cover SQL denominators, even-sample medians, as-of filtering, final-roster costs, empty or mixed-source populations, duplicate imports, conflicting snapshots, eligibility, partial-to-complete capture, safe HTML rendering, private projection, bearer/embargo handling and prohibited replay parameters. Four additional UI cases cover the embargo, partial-film exports, deliberate replay confirmation and locking. The browser journeys verify the owner header and downloaded bytes, an embargoed challenge, identical replay retries, the new draft, and 12 trace rows at both widths. These browser responses are invented and do not verify PostgreSQL permissions.

Six new PostgreSQL-only integration cases are included with the previous 96. They exercise actual receipt projection into SQLite, distinct fresh replays, preservation of the original film, ownership and guest claims, challenge embargo, guarded downgrade, rollback on link failure and concurrent identical requests. They were skipped because a runnable PostgreSQL service was unavailable; SQLite tests and static SQL parsing do not replace them. Run `docker compose --profile verification run --rm --build api-tests` locally before relying on those behaviors.

The prebuilt dashboard is generated from the exact same metrics code used by live imports. Checks reconcile the twelve starts and seven releases to source events, and the final hiring total to $7,860,000 across seven released films. No real participant observations, TMDB credentials or production telemetry were used.

Packaging starts from the Phase 11 archive (SHA-256 `707c656c33b54915c7ce7f55d3deee34f9a63c243c79c4fe0623e7c9073e7ed4`). Preservation includes the original game, configurable ports, setup/check scripts, test Dockerfile and savepoint fixture, previous migrations, scoring engine, frozen schemas, and prior README. The archive excludes credentials, private gameplay exports/marts, dependencies, caches and compiled build outputs. Its internal SHA-256 manifest and relative documentation links are checked.
