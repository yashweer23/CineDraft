# Phase 11 design

The lab answers one constrained question: how does replacing one cast or crew member affect a finished film under identical modeled conditions? It cannot edit a release or submit a score.

## Source and team boundaries

Every operation authenticates the owning guest/account and resolves the original draft. Challenge embargo is checked before reading lab data. A supported Phase 7 frozen production and a successful Phase 8 result must exist and pass source hash/schema checks. Candidate enumeration additionally validates the original sealed catalog bundle.

The baseline projects the frozen production into `phase11-team-v1`. This schema retains genre, pinned versions, budget, eight selections, role profiles, cards, graph configuration and twelve relationships. It omits historical offer IDs, live revisions and statuses. A hypothetical replacement is never forged into an official frozen snapshot or `Pick` row.

Refund the old locked fee, then charge the candidate's original role price. The original talent allowance and reserve remain fixed. Reject negative remaining funds, absent role profiles, a person already occupying another slot or a person outside the pinned pool. The candidate list is sorted by fee, then UUID, paginated at at most 50; the existing catalog limit is 5,000 role profiles. Original picks are exact controls.

Untouched selections, profiles, cards and relationships must remain identical. Rebuild relationships involving the replacement using the same pinned graph, not current TMDB observations. Shared movie titles/years come from that graph's dataset; exact credited jobs are retained. No upstream network request occurs during comparison.

## Versioned paired scenarios

`whatif-1.0` fixes 64 scenarios and the existing Phase 8 engine manifest. For each index 0–63, derive the sample seed as the canonical SHA-256 of `["whatif-1.0", source_input_hash, index]`. Pass that seed to the existing critics, audience and revenue streams. The same noise values feed both teams.

The original one-off release seed is not reused. Results describe an additional fixed sample, with the official output hash recorded for provenance. All alternatives to the same film share this sample. Request IDs and replacement IDs are absent from seed derivation. There is no “reroll scenarios” API.

Evaluate existing team inputs, score components and release math without modifying those functions. Reviews feed finance at their original unrounded precision. Dollar rounding and costs remain those of `simulation-1.0`. Decimal precision 64 with ROUND_HALF_UP surrounds the full computation, including interpolation.

Sort each metric sample. At percentile p use position `(n−1)*p`, interpolate between neighboring ordered values, and return full Decimal strings. For paired deltas, subtract within each scenario first, then summarize. Record P10, median, P90 and counts above/equal/below zero. Five metrics are included: critics, audience, gross, profit and ROI. These are descriptive outcomes under the game's invented model, not uncertainty estimates fitted to observed releases.

The deterministic studio score has no scenario range. Its component changes are explained separately, along with budget changes, selected talent/genre inputs, chemistry and evidence. Score rounding can hide a small unrounded change, so the API retains both.

## Persistence and recovery

One draft row lock serializes creation. Each variant is unique by draft, comparison version, slot and replacement identity. Store the full hypothetical inputs/output, their hashes, source hashes and deterministic analysis UUID in `whatif_analyses`. Store the validated request body/hash and analysis link in `whatif_receipts`, uniquely keyed by draft/request ID. Both inserts share a transaction.

A lost response replays its exact receipt. A new nonce for the same variant reuses the analysis and adds only a receipt. A reused nonce with different contents returns 409. A failed insert rolls back both tables. Reading history never runs the comparison engine. Authorization and embargo precede receipt/cache lookup.

SQL append-only triggers prohibit update/delete. Insert guards require a released film, matching official source, hypothetical schema/identity and a closed challenge. Receipt guards bind draft, request ID, slot and person to the analysis. Downgrade refuses to remove populated lab history. The database operator remains trusted, as in earlier phases.

No writes target official results, snapshots, picks, action records, submissions, budgets, status or revisions. Account claims change access through the existing ownership mapping without rewriting history.

The UI keeps a pending POST only in memory, displays the exact token-free recovery request, blocks conflicting navigation/account actions, and warns before unloading. A definitive failure clears the pending lock; a transport/5xx uncertainty retains it. Sign-in/restoration is required after tab/session loss. No public sharing, leaderboard promotion, multi-person optimization or client-controlled seeds are implemented.
