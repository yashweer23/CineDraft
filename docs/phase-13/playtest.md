# Phase 13 — human playtest worksheet

**Status: not yet conducted.** This blank worksheet is a plan, not evidence of observed players. The synthetic experiment and automated browser journeys do not count as human sessions.

Copy this file and [the CSV header](playtest-template.csv) into `validation-output/playtest/`. Use participant codes such as P01. Keep recovery tokens and account passwords out of notes and recordings.

## Small first study

Invite three to five people who have not implemented CineDraft. Ask each to use their usual computer or phone width. Record the catalog ID, genre, tier, browser, viewport and whether the participant has played a drafting game before. Use a genre/tier the catalog actually enables. Record exact counts; do not generalize a handful of observations to all players.

Give these tasks without explaining which buttons to press:

1. Start a film and preserve access so it can be reopened.
2. Inspect a candidate's evidence and choose a director. Explain the hiring allowance and production reserve in your own words.
3. Complete the roster. Preview a replacement, cancel it, then decide whether to use a recast.
4. Finalize and release. Explain one score component and the difference between box office gross and studio profit.
5. Restore access after reloading and find the saved film.
6. Run an original-person what-if control, then compare an affordable alternative. Explain what the paired comparison changes.
7. Export the film's gameplay events. Start a deliberate practice replay only if you want another film.

For each task record success, duration, whether help was required, exact observed behavior, and the participant's words where useful. Distinguish an observation from your interpretation. An expired token or an empty recast catalog is a setup constraint, not automatically a usability defect.

## Session record

- Participant code / date:
- Catalog ID / genre / tier / synthetic catalog yes or no:
- Browser / viewport / input device:
- Tasks attempted / completed without help:
- Point of confusion, observed behavior, and task:
- Participant explanation of reserve, profit, or paired samples:
- Proposed change and evidence supporting it:
- Follow-up result after a change:

Use Phase 12's owner export with `--cohort playtest --observed-human` only for actual observed participants' films. Use `internal` for your own development activity. The generated balance corpus never enters the gameplay analytics database. Reimport a participant's updated export into the same database/cohort; do not count retries as new sessions.

## Decision log

| Issue | Observation count / attempts | Impact on task | Proposed change | Implemented? | Retest outcome |
|---|---|---|---|---|---|
| No observations yet | — | — | — | — | — |

Choose a concrete observed problem, make the smallest useful change, and replay its affected automated journey plus a human retest. Preserve versioned rules and official results. Report unresolved issues and setup failures along with improvements.
