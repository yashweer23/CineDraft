# Phase 7 design

## Compatible version bundle

`prepare_drafting` verifies sealed dataset, supported computed feature/pricing schemas, graph algorithm and dataset identity, dependency manifest hashes, priced role nodes, and recalculated fees. It publishes immutable rules/scoring configurations and a sealed `draft_catalogs` row, then optionally appends a catalog activation. A dry run computes identical feasibility without writing. At least one tier must be feasible to publish.

A catalog pins dataset/features/prices/graph/rules/scoring. Creation uses the current activation; clients cannot select versions or seeds. Each draft's runtime row retains its catalog and owner. Subsequent activation never modifies a prior draft. The maximum supported pool is 5,000 priced role profiles; exceeding it fails publication.

## Exact distinct-person assignment

For `k <= 8` remaining slots, retain the `k` cheapest unused people per required professional role, breaking fee ties by person ID. This reduction preserves the optimum: if a solution uses someone outside a role's top `k`, at most `k-1` other people are occupied, so at least one no-more-expensive top-`k` person can replace them. Replacement preserves other selected people and roles. Four actor slots still require four distinct people.

Dynamic programming then processes each person once and tracks occupied-slot bitmasks. Read the DP state before processing that person, so multiple role profiles never allow that person to fill two slots. Store minimum cost and a deterministic lexicographic identity witness for each mask. There are at most 256 masks. Missing a full mask means no matching; an empty slot set costs zero.

Candidate legality requires its fee plus the exact remaining assignment cost to fit the available talent budget after excluding all picked people and this candidate. For efficiency, an optimal baseline witness can be reused when excluding a candidate outside that witness: removal cannot lower the optimum, and that witness still exists. Only witness members need a new solve. All fees are strict integer USD; equality is affordable.

These are feasibility checks, not game-balance certification. Enabled tiers can still have poor choice diversity. Reports expose role counts and short offers; catalog fairness and strategic balance remain later gates.

## Saved offers and transitions

Offer order derives from SHA-256 of version, server-generated seed, named stream and person ID. `sha256-order-1.0` avoids Python's process-randomized hashes and global random state. Persisted offers are authoritative and sealed; GET never draws new candidates.

Normal offers prioritize legal choices before disabled aspirational candidates. Rerolls prioritize fresh identities and retain at least one legal choice. A replacement with an identical set is rejected without consuming an allowance. There are at most three candidates; shortages are explicit.

| Current state | Action | Result |
|---|---|---|
| `awaiting_pick` | Select a legal current candidate | Record fee/pick; generate next slot, or enter `recast_available` after eight |
| `awaiting_pick` | Reroll, allowance remains | Save changed offer; consume one of two rerolls |
| `recast_available` | Preview a slot | Enter `recast_preview`; keep roster and money |
| `recast_preview` | Cancel current preview | Return to `recast_available`; retain cached alternatives |
| `recast_preview` | Confirm selectable alternative | Refund old fee, charge new fee; consume the one recast; enter `review_locked` |
| `recast_available` / `review_locked` | Finalize | Save immutable inputs; enter `production_finalized` |
| Any unfinished state above | Abandon | Preserve history, clear active offer, enter `abandoned` |

Recast streams depend on slot, not preview count. A per-slot cache additionally preserves exact offer IDs and cards through cancellation and other slot previews. The original selected person and all seven retained people are excluded. A preview can have no alternatives; cancel remains available. `generated_at_revision` records when the offer was saved; its response `revision` is the current draft revision, including reopened previews.

## Ownership, locks and receipts

Guest capabilities are 32 random bytes encoded as 43 URL-safe characters. Only their SHA-256 digest is persisted. Tokens expire after 30 days and can be revoked once. Tokens are sent only in `Authorization: Bearer ...`, never URLs. Private responses use `Cache-Control: no-store`. The inspector keeps its token in memory, masks it and supports manual recovery. No accounts, browser persistence, renewal or lost-token recovery are implemented.

A write transaction authenticates the session, locks the draft row, checks owner scope, checks a prior receipt, checks expected revision, validates the command, mutates picks/offers/money/state, and writes its receipt. Session shared locks prevent revocation from overtaking an in-flight operation; creation/revocation use exclusive session locks. Creation serializes requests for that session and keeps a separate creation receipt. Commits happen before service functions return responses.

Mutation idempotency is `(draft_id, command, request_id)`; creation is `(session_id, request_id)`. Canonical hashes cover validated request bodies (including normalized defaults). Same key/body returns the original saved response, even if the draft later advanced. Same key/different body returns 409. Ownership is checked before replay, so a request ID never grants access. Competing new actions at the same revision serialize: one commits and the other sees a stale revision. A receipt failure rolls back the entire action.

SQL exceptions are sanitized as 503. A commit acknowledgement can be lost; a failed response is not proof that a write did not commit. Retry the exact request with the same token, ID and body. The inspector blocks new writes while an outcome is uncertain and offers that exact retry. A 409 requires a fresh read and a consciously chosen new action. The API retains its existing three-second SQL timeout; contention may require retries.

This is a loopback local-development service. Production deployment would require account lifecycle, TLS, request limits and operational controls; none are introduced as part of this ZIP.

## Frozen inputs and migration

`0004_phase7` adds four tables (31 total), a nullable draft graph ID and an offer uniqueness constraint supporting current-offer foreign keys. Session history is retained; runtime owner/catalog/creation receipts cannot change. Catalogs require sealed sources. New graph pins must refer to a compatible sealed graph. Old migrations and existing rows are not rewritten. Downgrade refuses when graph-pinned drafts exist so ownership/history cannot be stripped.

Finalization stores `phase7-v1` inputs: eight matching cards and picks, integer fees, full selected role attributes/evidence, version IDs/hashes, seed, rules/scoring specification, graph configuration, and evidence for exactly the twelve designated roster relationships. No shared film produces a neutral absence message and zero bonus. The input hash covers canonical JSON. The embedded draft's `snapshot_hash` is null to avoid circular hashing; the live finalized response supplies the resulting hash.

Full selected role features preserve actor popularity and sparse-data flags needed by Phase 8. `scoring:baseline-1.0` freezes the Phase 1 formula specification; it does not execute it. `simulation-1.0` is a reserved implementation contract. No result row or release route is created. Phase 8 must implement that contract exactly or introduce an explicit new version without rewriting old snapshots.

`repository.load_snapshot` supports historical `phase3-v1` and new `phase7-v1` inputs. The new JSON schema is `contracts/snapshot.phase7.schema.json`; current HTTP routes are in `contracts/openapi.current.json`. Historical proposed contracts remain historical design material.
