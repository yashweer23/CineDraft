# Phase 9 design

## Authority and compatibility

The guided studio owns presentation, tab-memory credentials and the pending HTTP request. PostgreSQL and the existing API own catalog selection, offer order, legal choices, locked fees, balances, revisions, recast caching, immutable finalization and release outputs. No gameplay formula, seed or saved schema changes in this phase.

`Studio.tsx` selects the visual stage from the server's status. Genre and budget choices exist locally until creation. It renders a persistent budget strip, eight-slot roster, candidate cards, a review panel, confirmation dialogs and the existing release renderer. It does not store a client-calculated official result. Optional production titles are not added; saved films use genre and a short draft identifier.

`studioApi.ts` has one mutation lock per mounted studio. Controls block repeated submissions and do not switch tokens/drafts while a command is uncertain. POST request identity and body are retained before offering exact replay. Known 409 conflicts block writes until a fresh read. A confirmed POST followed by failed GET does not become an uncertain POST.

Every successful mutation/replay is followed by GET draft and GET roster. The second response must match both draft ID and revision. If another tab changes the draft between those reads, the screen blocks writes and asks for refresh. An older receipt is not treated as current state. A race after these reads still reaches the server's normal expected-revision check.

## Named roster endpoint

`GET /api/v1/drafts/{draft_id}/roster` returns `{draft_id, revision, members}`. Each member contains `slot`, `locked_fee_usd`, and the exact `LiveCard` from its persisted offer candidate. The service authenticates first, obtains the existing owner-scoped shared draft lock, reads ordered picks and verifies each card's person, role and fee against its locked pick. A recast reads the replacement pick's saved offer. The route is private and uses `Cache-Control: no-store`.

This is a separate read model so `LiveDraft` and the schema embedded in immutable Phase 7 snapshots do not change. It adds no table, migration, external request, current-data refresh or pricing calculation. Reading a released or abandoned draft cannot generate a new offer/result. Up to eight saved candidate lookups are bounded by roster size.

## Evidence and visual behavior

Candidate cards keep up to five notable films visible with title wrapping, matching credited jobs, source labels and source audience ratings. They show initials because the saved candidate contract lacks portrait URLs. Poster failures become neutral film placeholders. Dossiers use the card's pinned dataset/pricing/graph IDs for paginated full eligible filmography, attributes and shared-credit research. Those research pairs are labeled separately from the twelve scored slot relationships. Unavailable evidence never becomes fabricated neutral data.

The existing ReleaseInspector serves both guided and developer interfaces. Its heading uses a unique React ID, and financial cards now follow gross → studio receipts → production → marketing → total cost → profit. Computed values and half-up string formatting remain unchanged.

Native HTML dialogs supply modal focus containment. Escape and Close dismiss without a write. Closing restores focus to the original connected control; successful actions focus the next stage heading. A polite live region reports progress and completion. Visible labels, native radio groups, disabled explanations and 44px primary controls support keyboard use. The layout uses system fonts, no autoplay and reduced-motion rules.

The developer inspectors are retained in a native details section. Their session state is independent; switching tools does not transfer credentials implicitly. The guided studio itself stays mounted when those tools open or close.

## Boundaries

There is no account login, renewal, lost-token recovery, daily challenge, leaderboard, new simulation mode or deployment. No private credential is written to localStorage, sessionStorage, URLs or report exports. Token loss/expiry limits are explicit. Saved draft listings remain server-backed and paginated within their owning guest session.
