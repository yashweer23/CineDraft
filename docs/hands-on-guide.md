# Build CineDraft yourself — a hands-on guide

The goal is to understand the existing loop before moving it to React and FastAPI. You can play and edit this pack immediately. You do not need to finish the entire roadmap to start learning from it.

## Session 1: run it and trace one pick

Run `npm start`, complete one game, and open the saved film from “My filmography.” Then read code in this order:

1. `index.html` — find the `app` element and the order of the scripts.
2. End of `app.js` — `render()` starts the first screen.
3. `renderSetup()` — genre/budget controls lead to `C.start(...)` and `C.deal(...)`.
4. `pick(id)` — the current offer is checked, a candidate is pushed into the roster, and the next screen renders.
5. `affordable()`, `reserve()` and `deal()` in `engine.js` — understand why some cards are disabled.
6. `release()` in `engine.js` — distinguish game inputs from simulated outputs.
7. `normalize()` and `save()` in `app.js` — understand browser refresh and saved history.

Set a breakpoint inside `pick()`, draft a director, and inspect the state before and after. Write down which fields changed and why. This is more useful than replacing every file before you know the current flow.

## Session 2: make a small visible change

Change the subtitle in the setup screen or one accent color in `styles.css`, save and refresh. Find the CSS rule with the browser's Inspect panel before editing it. Run `npm test`; also confirm that buttons still look readable at a narrow width. These are low-risk practice edits, not a completed roadmap phase.

Next, change a fictional craft value for one person in `engine.js`, start a fresh game, and see where it appears. Restore it afterward if you want the exact original balance. The old save loader resolves current curated records, so old games can change when you edit those rows. That limitation is why the future design snapshots data.

## Session 3: understand the new specifications

Read the Phase 1 rulebook and data spec together. Explain these decisions in your own words:

- Why $10M total authorization gives only $6.5M to hire talent.
- Why a $500K candidate can still be unaffordable even with $600K remaining.
- Why a person who acts and directs must share one identity.
- Why a director's five notable works must be based on directing credits.
- Why a seed is insufficient without the same dataset, rules and actions.
- Why $30M box office does not mean the studio receives $30M.

Use the worked fixtures to calculate balances by hand. The important learning is turning these rules into invariants and tests, not memorizing the formula names.

## Session 4: begin Phase 2 deliberately

Save the extracted baseline in your own Git repository first if desired:

```sh
git init
git add .
git commit -m "Add CineDraft local prototype and Phase 1 design pack"
```

This creates local version history; it does not publish anything. Git may ask you to configure your own name and email before the first commit. Then use [the Phase 2 handoff](phase-02-handoff.md). Ask the agent to explain the new directory layout and run commands. Run them yourself and inspect a health response before adding domain features.

For each later phase, repeat: read acceptance criteria → implement a small slice → run it locally → inspect behavior → record what you learned → commit. Keep [the development log](development-log.md) as interview preparation.

## Keep changes aligned with the roadmap

| Phase | Your hands-on focus |
|---|---|
| 2–3 | Start both services, call an endpoint, inspect a migration and API schema |
| 4–5 | Trace one movie credit from source to normalized data and derived rating |
| 6 | Explain a chemistry edge using its supporting movie records |
| 7 | Reproduce a multi-role affordability edge case and show why it passes/fails |
| 8–9 | Inspect score contributions and complete the polished solo flow |
| 10–11 | Verify draft ownership and compare a replacement using the same seeds |
| 12–14 | Use analytics, measured tests, screenshots and a demo to present completed work |

Avoid rewriting all phases in one large prompt. Preserve working checkpoints and ask for explanations of the code you cannot yet explain yourself. Do not claim planned features or synthetic usage as real resume achievements.

## Manual check after interface edits

- Start each existing genre at least once and switch budgets before drafting.
- Use a reroll, confirm it changes offers and consumes one allowance.
- Make a pick, refresh, and verify the same roster and remaining money.
- Complete eight unique slots without overspending and release the film.
- Confirm result metrics, full credits and saved film history appear.
- Try keyboard navigation, a narrow browser and a long film title.
- Check the browser console for runtime errors.
- Confirm that restarting a new brief prompts before abandoning an unfinished draft.

The new Phase 1 rules have their own future acceptance checks in the state/edge-case document. Do not treat the legacy checks above as evidence that those future features are implemented.
