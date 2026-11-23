# Owner export and explicit practice replay

Both operations use the existing bearer header and private draft ownership rules. Responses have `Cache-Control: no-store`. Both enforce the challenge deadline before exposing exports, cached replay responses or creating a new film. There is no public aggregate/export-all endpoint and no background collection.

| Endpoint | Accepted input | Output |
|---|---|---|
| `GET /api/v1/drafts/{draft_id}/analytics-events` | Owning guest or account session | `gameplay-events-1.0`, for this film only |
| `POST /api/v1/drafts/{draft_id}/replay` | `{"request_id":"<new UUID>"}` plus owning session | Original creation response for the new practice draft |

The export has an allowlist: pseudonymous session key, start and capture times, brief and version labels, catalog-source marker, practice/closed-challenge marker, budget allocation, stable events, and eligible opportunities. It does not include passwords, bearer credentials, request bodies, snapshots, original draft UUIDs or simulation seeds. Hiding identifiers is not anonymization: exact times and casting decisions can still identify a known playtest. Only share deliberately. Access revocation prevents new downloads; it cannot retract offline copies.

Authoritative server auth runs before reading a film. A database draft lock provides a coherent view of the source receipts. Exact retries, saved-variant replays and repeated exports do not create picks or completions. Guest claims transfer future API access using the existing ownership mapping.

A successful source release is required for a new practice replay. The server supplies the source's pinned catalog, genre and budget; it generates a fresh seed. The caller cannot pick a seed, tier, price, or challenge. The new film has zero picks and revision zero. The server creates its normal draft, offer and parent-child link in one transaction. The link is immutable and unique per parent/request. Retrying the identical request even after the child has advanced returns its creation receipt; the studio then loads the child's current revision and roster. Distinct request IDs are intentional new films. Replay children never submit the parent’s score.

The export can be downloaded for unfinished films: the UI keeps the download button available and hides the replay action until release. Open challenges return 423 throughout. Wrong/expired owner credentials return 401/404 as appropriate. A replay of an unreleased source returns 422. A database outage returns a sanitized 503. For a lost replay response, keep the exact path/body and use **Retry same request**. For a lost download, repeat GET. For manual replay recovery, use [the existing exact-request recovery instructions](../phase-11/api.md#manual-exact-request-recovery-in-powershell) with the saved `/replay` path and its original single-field body.

Contracts: `contracts/gameplay-events.phase12.schema.json`, `contracts/practice-replay.phase12.schema.json`, and `contracts/openapi.current.json`. Regenerate from `backend/` with `python -m scripts.export_phase12_contracts`.
