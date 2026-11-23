# Phase 11 verification — 3 November 2026

| Check | Observed result |
|---|---|
| Backend suite, Python 3.12 | **340 passed; 96 PostgreSQL tests skipped** |
| Frontend component suite | **51 passed** |
| TypeScript / Vite production build | Passed |
| Original game and local server suite | **4 passed**, including 540 complete synthetic drafts |
| Phase 11 browser journey | **2 passed** with mock HTTP: 1280px desktop and 390px mobile |
| Offline migration SQL | **152 statements parsed**, including **25 PL/pgSQL functions** |
| PostgreSQL runtime, metadata comparison, locking and rollback | Not run in this environment; run the provided PostgreSQL suite |
| Docker builds, native Windows setup and browser → live API → database | Not run here |

The 44 new backend unit cases exercise paired math, exact zero controls, repeatability across Decimal contexts, percentile interpolation, immutable input projections, invalid replacements, budget rejection, bounded requests, header authentication, embargo handling and saved-report integrity. A separate calculation reconstructs the paired profit distribution from the individual Phase 8 scenarios. The synthetic director change adds $43,750 in hiring cost and moves the deterministic studio score from 66 to 68.

Six new component checks cover lazy loading, unaffordable alternatives, exact retries, parent locks, definitive session errors, history reads, report interpretation and cleanup. The two new browser journeys use a real Chromium browser with invented API responses. They cover eight picks, submission embargo, post-close access, an exact zero control, interrupted comparison, disabled sign-out/navigation, identical-body retry, explanation and saved-history retrieval. Both viewports passed page overflow checks. The mobile report was inspected visually; it displays original, replacement and change together for each metric, with ROI changes labeled in percentage points.

Fourteen new PostgreSQL-only cases accompany the prior 82. They cover actual role/identity rejection, cross-owner privacy, guest claim and revocation, sealed catalog prices, exact replay, caching, official-row preservation, two-table rollback, immutable rows, guarded downgrade, challenge embargo and independent-connection races. None of these 96 cases passed or failed here: they were skipped for lack of a PostgreSQL runtime. SQL parsing and mock browser tests cannot verify database trigger execution. The root README gives the local commands.

The ZIP is based on the preceding Phase 10 release (SHA-256 `dddd145cd10df092f4ca61eba128e9955beb18ae925c6f780fdf1d3c286507e0`). Packaging compares the original game assets, stack setup, Docker test-image fixes, savepoint fixture, historical migrations, baseline rule/engine files and frozen schema contracts against it. The prior root README is preserved as `README-phase10.md`. Archive validation checks CRCs, every SHA-256 manifest entry, JSON/Python syntax, relative Markdown file links and exclusions for private environment files, tooling, build artifacts and credentials.
