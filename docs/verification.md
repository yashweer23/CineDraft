# Verification report

Date: 20 October 2026. Scope: this local source-and-documentation package, including the preserved Phase 0 prototype. These results do not verify future Phase 1 game-rule implementation.

## Checks completed

| Check | Observed result |
|---|---|
| Original source preservation | `index.html`, `styles.css`, `app.js` and `engine.js` exactly match the existing deployment archive |
| JSON configuration | package.json and VS Code configurations parse successfully |
| Legacy engine coverage | 540 completed drafts: 6 genres × 3 budgets × 10 seeds × 3 strategies |
| Strategies | Cheapest legal offer, most expensive legal offer, best genre-fit offer |
| Rerolls | Each simulated draft exercises all 3 legacy offer rerolls |
| Engine assertions | Unique identities, correct roles, legal continuation, no overspend, completed roster, deterministic result and weekly totals matching gross |
| Invalid cases | Unsupported legacy genre/budget and incomplete release are rejected |
| Local HTTP server | The four application assets return HTTP 200 with content; HEAD works; unknown/internal routes return 404; POST is rejected |
| Automated suite | 4 test cases passed, 0 failed; final observed run approximately 0.44 seconds, not a performance benchmark |

Checks ran with Node.js **v24.19.0** on the provided Linux environment. The package specifies Node 22+ and uses built-in APIs, but a separate Windows/Node 22 run was not performed. Windows-friendly commands are included; this is not a claim of completed cross-platform certification.

## Browser verification limitation

A headless Playwright smoke run was attempted for 1280px and 390px layouts, refresh recovery and a complete UI journey. It could not start because the runtime has no installed Chromium executable, and no system Chrome/Chromium was found. Therefore **no browser journey, visual layout, mobile overflow, clipboard, accessibility or keyboard result is claimed for this delivery**. The original UI files are unchanged.

Use the manual checklist in [hands-on-guide.md](hands-on-guide.md) after starting the game locally. The test suite covers engine invariants and local serving, not rendering.

## Package checks

Before creating the ZIP, local Markdown links, required document paths, JSON syntax and source preservation were checked. The archive contains a single `CineDraft-VSCode/` root, with no node_modules, credentials, deployment metadata, browser saves or generated screenshots. A checksum manifest records every included file except itself. The ZIP's integrity and an extracted copy's automated tests are checked during packaging.

## Re-run

```sh
npm test
```

There is no test dependency installation. The legacy tests intentionally use $90M/$140M/$200M and three offer rerolls. When implementing new rules, keep them labeled as legacy checks and add new tests for integer USD, exact assignment, two rerolls, final recast and source-verified credits.
