# Phase 10 verification — 1 November 2026

| Check | Observed result |
|---|---|
| Backend suite on Python 3.12.14 | **296 passed; 82 PostgreSQL tests skipped** |
| Targeted account/token/API regression after final token-namespace fix | **34 passed** |
| Frontend component suite | **45 passed** |
| TypeScript and Vite production build | Passed |
| Original game / local server | **4 passed**, including 540 complete synthetic legacy drafts |
| Guest browser journey | **2 passed**, desktop 1280px and mobile 390px; mock HTTP |
| Account/challenge browser journey | **2 passed**, desktop 1280px and mobile 390px; mock HTTP |
| Offline migration SQL | **143 statements parsed**; all **24 PL/pgSQL function definitions parsed** |
| PostgreSQL runtime, migration metadata comparison and concurrency | **Not run here**; execute the included local suite |
| Docker builds, Windows execution and real browser → API → PostgreSQL | **Not run here** |

The frontend build used Node 24.22.1 and existing locked dependencies; the optional browser checks used Playwright 1.51.1 with its Chromium 134.0.6998.35. The backend adds pinned tzdata 2025.2 for systems without IANA timezone files. Windows installation itself remains unverified.

The 34 new backend unit cases exercise real scrypt hashing, secret redaction, username/token validation, calendar/DST boundaries, forbidden challenge inputs, public seed projection, authentication gates and HTTP error contracts. The final targeted regression also covers a 43-character guest token that happens to start with `acct_`; only the full 48-character account shape selects account authentication.

The 16 new PostgreSQL cases cover claims and account privacy, password/session revocation, durable username throttles, one attempt and exact replay, shared offer streams, publication immutability, deadline/seed/result embargo, submission rollback, guarded downgrade, ranking ties/pagination, catalog pinning and independent-connection races. All 82 database cases, including earlier phases, require an actual PostgreSQL connection. Static parsing is not evidence that constraints, locks or migrations execute correctly.

Guest browser checks include eight picks, an interrupted response with exact retry, recast cancellation, finalization, saved release and token restoration, Escape/focus and an additional 640px reflow viewport. Account browser checks include registration, explicit one-attempt entry, eight picks, release with no early report request, embargoed rankings, post-close report/ranks/seed, memory-only storage and sign-out. Both widths were checked for page overflow; mobile ranking typography was visually inspected and corrected. These browser runs use invented responses and do not validate database ownership or score persistence.

The six new account/challenge component cases cover memory-only sign-in, claim acknowledgment and field clearing, password revocation, wrong-current-password handling, exact interrupted challenge replay and hidden report behavior, plus anonymous post-close rankings/audit. Earlier guest and inspector tests remain passing.

Preservation checks compare the prior ZIP against original gameplay assets, Compose/env examples, setup/stack scripts, test Dockerfile/savepoint fix, Alembic configuration, all five historical migrations, frozen rule/engine sources and Phase 7/8 schema artifacts. The new ZIP excludes private environments, browser tooling/screenshots, dependencies, build output and caches. Its SHA-256 file manifest is verified against every packaged file.

Run the root README's database commands and [two-account exercise](hands-on.md) before treating the persistence/competition gates as passed. Real TMDB credentials, Internet hosting, broad abuse testing, screen-reader testing and native browser-menu zoom were not part of this packaging run.
