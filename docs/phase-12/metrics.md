# What each number counts

**Unit:** one modern draft (one analytic session). Starts, events and selectable opportunities come from the private server records for that film. An analytics session does not identify a unique person, browser visit, or login. The database sees issued offers and accepted choices, not every scroll, click, card impression, or period of active attention.

**Population:** choose exactly one of `demo` (generated samples), `internal` (developer/test use; default for owner exports) or `playtest` (operator-attested observed human activity). `fixture` is an independent catalog attribute. The local analytic store represents only the files actually captured. If you only export released films, its completion rate is subject to selection bias. Capture starts and follow up unfinished films too.

**Window:** `--from` includes starts at that time; `--until` excludes starts at or after it. `--as-of` includes events at or before the cutoff for those starts. Date-only values mean 00:00 UTC. To include October 12, use an exclusive end of October 13. A start-window end is not a follow-up cutoff. No film can be observed past its latest imported snapshot; an unfinished film may have continued after capture. If transaction times reverse, later revisions are not made visible until their predecessors' timestamps have passed. Negative wall-clock intervals are excluded from medians and counted separately.

| Event | Source / identity |
|---|---|
| `start` or `replay_start` | One per draft. A replay start requires a saved explicit parent → new practice-film link. |
| `pick`, `reroll`, `preview_recast`, `cancel_recast`, `confirm_recast`, `finalize`, `abandon` | Committed game action receipt, ordered by revision. Failed/rejected requests do not become choices. |
| `release_failed` | Persisted failed official simulation attempt (not a completion). |
| `release` | First successful release, including a successful retry; score/profit come from the matching official result. |
| `whatif` | One per saved hypothetical variant, independent of the number of requests to retrieve it. No alternate scores/profits are exported. |

IDs are SHA-256 hashes of canonical JSON `["gameplay-events-1.0", kind, source_identity]`. The session, start, action, offer, and what-if namespaces are distinct. A start contains no owner/token field; a pick keeps the eligible talent ID and hashed offer key. Exposing a saved offer again does not create another opportunity. Snapshot downloads and transport retries are not analytics events.

**Funnel:** the denominator is distinct starts in the selected population. Initial picks advance one stage; confirmed recasts do not add a ninth pick. Finalized and released are separate. Explicit abandon is a terminal action. Anything neither abandoned nor released at observation is unfinished, not an inferred quit. Replays count as starts as well as in the replay subset.

**Round time:** use the first committed pick in each slot. For director, start at draft creation; for the next slots, start at the previous committed initial pick. Include intervening rerolls and time away. Median is the middle observation for odd n and mean of the middle pair for even n. Unmade picks have no measured duration; compare their funnel counts separately.

**Talent selection:** group by public talent ID and slot, not just name or broad role. Each selectable candidate in a distinct initial-round offer contributes one opportunity, even if that offer was rerolled or the draft stopped there. A pick contributes one corresponding selection. Division by zero gives no rate, not 0%. Final release success is grouped by the actual final roster after recasts. Mean studio score and fictional profit are simple per-release means with their sample size. These are associations within a selected sample and model, not causal effects or actual film performance.

**Genre and budget:** genre share counts all starts. Budget allocation uses only officially released films. Take the most recent selection in each slot, sum its locked fee once, and reconcile talent spend + unused allowance + reserve to the total allocated budgets. Utilization = sum of fees / sum of talent allowances. Marketing remains outside the original allocation; no imaginary comparison costs are added.

**Versions and limits:** filters are bound SQL parameters. Report catalog, rules, scoring, simulation and fixture breakdowns before combining cohorts. Empty samples show unobserved statistics as a dash. Percentage and mean presentation uses the rounding in `metrics.sql`; source fees/profits are integer USD. Large offline reports may produce large scrollable tables. This phase establishes measurement definitions for Phase 13; throughput and cross-catalog balance are not benchmarked here.
