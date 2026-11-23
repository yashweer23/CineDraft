# Phase 9 — full drafting and results interface

Continue the cumulative VS Code ZIP plus standalone README workflow. Do not deploy a site. Preserve the user's private `.env` files, ports 5433/8001/5174, original four game assets, historical migrations and saved inputs/results. Current migration head: `0005_phase8`; current API version: 0.8.0.

## Read and verify first

Read the Phase 1 UX/game specifications, Phase 7 ownership/drafting design and Phase 8 scoring/API/recovery/verification documents. Inspect current frontend inspectors and API contracts before changing the flow. Run real PostgreSQL checks: the Phase 8 package observed 258 backend unit passes, 30 frontend passes and 4 legacy passes, but all 64 PostgreSQL cases were skipped here. Browser visual and end-to-end checks also remain unverified.

## Implement Phase 9

1. Turn the existing learning inspectors into a clear brief → draft room → review/recast → finalize → release → report journey. Keep the inspectors available for hands-on learning where useful, without making raw JSON the primary product experience.
2. Improve responsive layouts, accessible keyboard navigation, visible focus, status announcements and loading/error states. Validate desktop and mobile layouts with actual browser checks.
3. Present three server-offered candidate cards with role, fictional price, source-backed top-five works and clear legal/blocked explanations. Show remaining money, reserved production and the eight-slot roster throughout. Do not derive official eligibility or fees in the browser.
4. Make the two rerolls and optional cached recast understandable. Preserve cached preview IDs, cancellation behavior, exact refunds, unique-person rules and server revision authority.
5. Make guest-token creation/restoration and its expiry/limitations understandable. Preserve current memory-only handling unless an explicit account/security design is implemented. Do not introduce token leaks through URLs, logs or public exports.
6. Preserve the distinction between retrying the same uncertain HTTP command and issuing a new retry after a confirmed simulation failure. Successful films have one immutable result, never a client-side reroll.
7. Build the results experience around separate studio score, simulated reviews, explanation contributions, source coverage and complete financial reconciliation. Show pinned shared-film evidence with correct person/job orientation and weekly gross that sums exactly.
8. Keep state recoverable from the API after refresh. Display original saved receipts appropriately, then read current state; do not overwrite newer server state with assumptions from stale tabs.
9. Add meaningful frontend interaction and browser-to-API/database tests for the entire journey, authorization, recovery, repeated clicks, stale revisions and error paths. Document any browser or database gate that remains unrun.
10. Regenerate any changed current API contracts, provide updated setup and hands-on instructions, package the cumulative ZIP and write the next handoff. Do not expand into later-mode gameplay, accounts/leaderboards, what-if analytics or AI without explicit scope.

## Boundaries that must not change silently

- `phase7-v1` snapshots and `phase8-v1` results are immutable. Existing `scoring:baseline-1.0`, `simulation-1.0` and their manifests must retain behavior for replay. Balance changes need explicit new versions.
- Offer ordering uses `sha256-order-1.0`; release noise uses separate `sha256-uniform53-1.0` streams. Client seeds/noise overrides are forbidden.
- Release and retry execute synchronously in one database transaction. `simulation_running` is intermediate, not a queued durable job. SQL failures roll back the full command; compute failures can create a safe failed attempt.
- A command ID/body replays its original receipt even after a later command succeeds. Authentication comes before replay. Result reads never simulate.
- Marketing is an additional modeled cost. Gross, studio receipts and all-in profit are distinct. UI rounding must not alter saved arithmetic or turn unspent talent authorization into production spending.
- No shared evidence means neutral absence, not a claim that people never collaborated or are personally incompatible.
