> Historical Phase 1 README. See [README.md](README.md) for the current Phase 2 package.

# CineDraft — local prototype + Phase 1 design pack

Draft your own movie: choose a genre, hire eight cast and crew members, and simulate a fictional release. This ZIP gives you editable source and the design documents to develop CineDraft yourself in VS Code.

**Current delivery: the original playable prototype, plus completed Phase 1 specifications. Phase 2 and the remaining full-stack roadmap are not implemented.**

## Run in VS Code

1. Extract the ZIP completely.
2. In VS Code choose **File → Open Folder** and open `CineDraft-VSCode`, the folder containing this README and `package.json`.
3. Install Node.js 22 or newer if needed. Open **Terminal → New Terminal**.
4. Run:

```sh
npm start
```

5. Open **http://127.0.0.1:5500** in your browser.

There are no npm dependencies to install, no build step, no API key, and no database for this version. Edit the source, save, and refresh the browser. Stop the server with **Ctrl+C**.

If PowerShell blocks `npm.ps1`, use `npm.cmd start` or `node scripts/serve.cjs`. For a different port use `npm start -- 5501`. See [the detailed Windows/macOS/Linux guide](docs/setup-vscode.md), including the Python alternative and debugger setup.

## What works now / what the docs specify next

| Feature | Runnable prototype | Phase 1 target design |
|---|---|---|
| Genres | Crime, Sci-fi, Drama, Comedy, Horror, Action | Ten genres including Adventure, Mystery, Romance, Thriller |
| Budget | $90M / $140M / $200M; values stored in millions | $10M / $50M / $200M; integer USD |
| Reserve | Fixed $25M combining production and marketing | 35% non-talent production only; marketing separate |
| Draft | Eight slots, three candidates per round | Same structure; verified role eligibility and person IDs |
| Rerolls | Three, called “recasts” in the old UI | Two offer rerolls plus one optional completed-roster recast |
| Candidate works | Not present | Up to five verified, role-specific films visible on each card |
| Ratings and chemistry | Curated fictional values and shared genre affinity | Explainable data-derived ratings and shared-credit evidence |
| Storage | Browser localStorage | Server persistence in later phases |
| Release | Existing simplified fictional simulator | Versioned, explainable simulation in Phase 8 |

The four original gameplay files are preserved byte-for-byte. The new budget and top-five requirements are **designs**, not features already added to this prototype. This preserves the attached Phase 1 instruction to avoid implementing later phases.

## Read these first

1. [Hands-on development guide](docs/hands-on-guide.md) — understand and change the current code.
2. [Prototype inspection](docs/prototype-audit.md) — existing behavior, limitations, migration gaps.
3. [Game rulebook](docs/phase-01/game-rulebook.md).
4. [Scoring design](docs/phase-01/scoring-design.md).
5. [Talent data and top-five ranking](docs/phase-01/talent-data-spec.md).
6. [UI/UX blueprint](docs/phase-01/ui-ux-blueprint.md).
7. [Game states and edge cases](docs/phase-01/game-state-and-edge-cases.md).
8. [Phase 1 summary and checklist](docs/phase-01/phase-01-summary.md).
9. [Phase 2 handoff](docs/phase-02-handoff.md) — your next agent prompt.
10. [Full development roadmap](docs/CineDraft_Development_Roadmap.md).

The original supplied brief is retained in [phase-01-request.md](docs/phase-01-request.md). The Phase 1 documents resolve its defaults and supersede conflicting Phase 0 rules in the earlier roadmap.

## Project map

| Path | Purpose |
|---|---|
| `index.html` | Page shell, script order, modal, header/footer |
| `styles.css` | Existing responsive visual design |
| `app.js` | Screen rendering, event handlers, autosave, history |
| `engine.js` | Curated roster, draft feasibility, seeded offers, existing release formula |
| `scripts/serve.cjs` | Dependency-free local development server |
| `tests/` | Current prototype engine and local-server checks |
| `.vscode/` | Optional run/test tasks and Chrome debugger configuration |
| `docs/` | Setup, design, learning guide, future roadmap and handoff |
| `docs/verification.md` | What was actually checked for this delivery |
| `MANIFEST.sha256` | Checksums for package contents except the manifest itself |

## Check your changes

```sh
npm test
```

Checks exercise 540 completed legacy drafts and local HTTP startup. They do not establish that the future Phase 1 rules have been implemented. Use the manual checklist in the hands-on guide after UI edits.

## Data and storage

Names are real; all talent attributes, fees, chemistry, reviews, and commercial results in this prototype are fictional game values. There is no TMDB integration or verified filmography dataset yet. Existing team entries are not authoritative identity records.

Progress is stored under `cinedraft-v1` in the browser for the exact host and port you use. The hosted version's saved games do not automatically appear locally. Different browsers and ports have separate storage. The app keeps up to 30 completed films.

Only optional Google Fonts need internet; gameplay uses local files and falls back to system fonts offline. No secret belongs in `app.js`, `engine.js`, or other browser-served source. Add future TMDB credentials to a backend environment only.

## Future architecture

React + TypeScript frontend → FastAPI application → PostgreSQL, with a separate import command for TMDB metadata. See [architecture notes](docs/architecture.md). Keep the project as one application and one database initially. No deployment is required to learn or develop locally.
