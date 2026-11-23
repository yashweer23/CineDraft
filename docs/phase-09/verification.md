# Phase 9 verification — 28 October 2026

## Checks run

| Check | Observed result |
|---|---|
| Backend units | 262 passed in the full run; final API-description/export change also checked with 11 relevant passes |
| Frontend components | 39 passed across six files |
| TypeScript / production Vite build | Passed |
| Original game | 4 passed, including the 540-draft invariant exercise |
| Real Chromium journeys with mocked HTTP | 2 passed: 1280px and 390px |
| Additional reflow | 640px CSS viewport, equivalent to the available width at 200% zoom on a 1280px window |
| Visual inspection | Desktop draft room, mobile candidate, mobile financial report and reflow screenshots inspected |
| Current contract | OpenAPI regenerated; one new authenticated GET roster path |
| Preservation | Original game, migrations, frozen snapshot/result schemas, scoring engine and dependency pins checked against Phase 8 |

Runtime: Python 3.12.14, Node 24.22.1. Browser tooling was isolated from app dependencies: Playwright 1.51.1 / Chromium 134.0.6998.35. The default newer runtime browser download failed; the isolated browser installation succeeded. No browser dependency or binary is bundled into the ZIP.

The new component cases cover save-token acknowledgement, all five visible works, disabled candidates, cancel/confirm, saved names, next-round focus, lost-response exact replay, older receipts followed by current reads, stale revisions, committed POST with failed follow-up GET, restored sessions, recast cancellation/refunds, finalization, one release and dossier pagination/image fallback/Escape. Existing inspector and release cases remain in the suite.

The browser runner uses actual DOM, CSS, native dialogs and browser layout. Its default mock API is explicitly isolated in `frontend/e2e/mock-api.mjs`, never imported by application code. Tests cover the eight-pick journey, first-pick lost-response recovery, cached-preview cancellation, finalization, release, page refresh, token restore, reading the saved report, dossier Escape/focus and no horizontal document overflow. Mock mode does not verify real SQL, hashing, ownership or gameplay math. The report fixture contains invented values solely for display checks.

## Gates not run here

**66 PostgreSQL integration cases were skipped, not passed.** No usable PostgreSQL runtime or `TEST_DATABASE_URL` was available. There are 64 preserved Phase 8 cases plus two new named-roster cases. The new tests verify exact saved-card reads, unchanged preview/cancel roster, replacement cards/fees, immutable snapshots after release, wrong-owner denial and revoked sessions. Existing savepoint isolation remains intact.

The browser script also supports `CINEDRAFT_E2E_LIVE=1`. It refuses non-synthetic catalogs and creates its own guest sessions and films against a real running API/database. **That live mode was not run here.** It intentionally leaves its synthetic history intact; it does not delete application data.

Windows PowerShell execution, screen-reader use, native browser-menu zoom, other browser engines and production load were not checked. Reflow testing at an equivalent viewport is not a claim that native browser zoom was exercised. There was no deployment or live TMDB import.

## Run locally

Follow the root README for unit/build/legacy checks, real PostgreSQL tests, and mock/live browser commands. Generated browser screenshots belong in ignored `test-results/browser/`; private token values are not logged by the runner. The packaged ZIP excludes screenshots, browser binaries, dependencies, private environment files, caches and build output.
