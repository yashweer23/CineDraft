# Phase 7 API and recovery

Base URL for your native host: `http://localhost:8001/api/v1`. In the studio, use relative `/api/v1` URLs through Vite. Interactive schemas are at `/api/docs`. Current code and `contracts/openapi.current.json` are authoritative; Phase 3's proposed OpenAPI is historical.

## Routes

| Method and path | Authorization | Purpose / body |
|---|---|---|
| `POST /sessions` | None | Create 30-day guest capability; returns token once |
| `POST /sessions/revoke` | Bearer | Revoke this session; prevents further draft access |
| `GET /catalog` | None | Active server-selected catalog, exact tier feasibility |
| `POST /drafts` | Bearer | `request_id`, `genre_id`, `tier`, optional `mode: classic` |
| `GET /drafts?limit=5&offset=0` | Bearer | Your saved drafts; maximum page size 20 |
| `GET /drafts/{id}` | Bearer | Current saved draft/offer; never regenerates offers |
| `POST /drafts/{id}/picks` | Bearer | Common fields plus `offer_id`, `person_id` |
| `POST /drafts/{id}/rerolls` | Bearer | Common fields plus `offer_id` |
| `POST /drafts/{id}/recast/preview` | Bearer | Common fields plus `slot` |
| `POST /drafts/{id}/recast/cancel` | Bearer | Common fields plus `offer_id` |
| `POST /drafts/{id}/recast/confirm` | Bearer | Common fields plus `offer_id`, `person_id` |
| `POST /drafts/{id}/finalize` | Bearer | Common fields only |
| `POST /drafts/{id}/abandon` | Bearer | Common fields only |

Common mutation fields are a fresh UUID `request_id` and integer `expected_revision` copied from the current draft. UUIDs identify commands, drafts, offers and people; a draft UUID does not authorize access. The owner token goes only in `Authorization: Bearer TOKEN`. Fees, seed, eligibility, versions, state and scores are server controlled; extra body fields are rejected.

No `/release`, `/retry-simulation` or result endpoint is mounted. Finalization freezes inputs, not results.

## PowerShell: create, pick and replay

Run these snippets in a private PowerShell terminal. To reuse the studio's session without echoing its token:

```powershell
$api = 'http://localhost:8001/api/v1'
$secureToken = Read-Host 'Your recovery token' -AsSecureString
$ownerToken = [System.Net.NetworkCredential]::new('', $secureToken).Password
$headers = @{ Authorization = "Bearer $ownerToken" }
```

Alternatively create a separate session with `$session = Invoke-RestMethod -Method Post "$api/sessions"`, then set `$ownerToken = $session.access_token`. Save the token privately. Do not paste it into shared screenshots, commit it, put it in a URL or use it as a TMDB credential.

Create an available tier (check `GET /catalog` first):

```powershell
$createBody = @{
    request_id = [guid]::NewGuid().ToString()
    genre_id = 'drama'
    tier = 'studio'
    mode = 'classic'
} | ConvertTo-Json
$draft = Invoke-RestMethod -Method Post "$api/drafts" -Headers $headers -ContentType 'application/json' -Body $createBody
$draft | Select-Object draft_id, status, revision
$draft.current_offer.candidates | ForEach-Object {
    [pscustomobject]@{ name=$_.card.name; person_id=$_.card.person_id; fee=$_.card.hiring_fee_usd; selectable=$_.selectable }
}
```

Pick the first selectable candidate as a learning exercise:

```powershell
$candidate = $draft.current_offer.candidates | Where-Object selectable | Select-Object -First 1
$pickBody = @{
    request_id = [guid]::NewGuid().ToString()
    expected_revision = $draft.revision
    offer_id = $draft.current_offer.offer_id
    person_id = $candidate.card.person_id
} | ConvertTo-Json
$pickUrl = "$api/drafts/$($draft.draft_id)/picks"
$picked = Invoke-RestMethod -Method Post $pickUrl -Headers $headers -ContentType 'application/json' -Body $pickBody

# Repeat the exact same request. No second charge or revision increase.
$replayed = Invoke-RestMethod -Method Post $pickUrl -Headers $headers -ContentType 'application/json' -Body $pickBody
$picked.revision -eq $replayed.revision

# Read current state before choosing another action.
$draft = Invoke-RestMethod "$api/drafts/$($draft.draft_id)" -Headers $headers
```

Expected replay comparison: `True`. Repeat the candidate/body construction for each subsequent slot, using a new request ID for each consciously chosen new pick. Never increment revisions locally or send a client-calculated fee.

## Recovery rules

- **Timeout, connection loss or 5xx:** the commit outcome may be unknown. Reuse the exact saved URL, body and token. A committed request returns its stored response; an uncommitted one executes once. Keep `$createBody` or `$pickBody` until the outcome is known.
- **409 stale revision/offer:** read the current draft. If the desired action is still appropriate, construct a new request using the current revision/offer and a new ID.
- **409 idempotency conflict:** the same command ID already belongs to different validated fields. Recover its original request; do not alter fields and call it a retry.
- **Replay after later actions:** the response intentionally describes the original action. GET returns the latest state.
- **401:** the capability is missing, unknown, expired or revoked. A matching UUID, body or receipt cannot bypass authentication.
- **404 for another owner's draft:** ownership is deliberately not disclosed to other sessions.

The browser's uncertain-request panel displays `{path, body}` without a token. To recover it after a tab closes, save that JSON privately, restore the owner token as above, and submit `"$api$($saved.path)"` with `($saved.body | ConvertTo-Json -Depth 10)`. This performs the original request; it is not a new draft action. Avoid closing the tab before saving both the token and uncertain request.

Mutation receipts are keyed by draft + command + request ID; creation receipts by owner session + request ID. Validated bodies normalize optional defaults and ignore JSON whitespace/key order when hashing. Changing any substantive field conflicts.

## Response details

`budget` reconciles reserve, talent budget, spend and remaining money. `minimum_remaining_cost_usd` is the exact minimum for unfilled slots excluding picked people; zero means no remaining slots, not a free full roster. Abandoned drafts return null. `can_reroll` explains pool or allowance limits.

An offer returns its saved candidates, `selectable` and `blocked_reason`. A reopened recast has the original `offer_id` and `generated_at_revision`, but its `revision` matches the current draft. Use the draft's current revision for actions.

Finalized responses include `snapshot_hash`. The frozen seed and complete input data are persisted server-side; the live view does not reveal the seed during drafting. Snapshot JSON is described by `contracts/snapshot.phase7.schema.json`. There is no public snapshot or seed endpoint in this phase.

All errors contain a structured `error` plus diagnostic `request_id`; stale errors also include `current_revision`. The diagnostic response request ID is different from the command ID you supplied. Private responses are `Cache-Control: no-store` and never include the bearer token except the explicit new-session response.

## Revocation

```powershell
# Intentional: this token will no longer grant access to any of its drafts.
Invoke-RestMethod -Method Post "$api/sessions/revoke" -Headers $headers
```

Revocation keeps data and receipts but blocks further access. It is not a logout or a token rotation. A new session does not inherit the old session's drafts.
