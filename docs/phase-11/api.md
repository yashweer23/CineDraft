# Phase 11 API and recovery

Use `Authorization: Bearer <owning-session-token>`. Both guest and account sessions are supported. Query-string tokens are ignored. All routes return `Cache-Control: no-store`.

Base: `/api/v1/drafts/{draft_id}/what-if`

| Method/path | Purpose |
|---|---|
| `GET /candidates?slot=director&limit=12&offset=0` | Original card, refund allowance and paginated pinned alternatives |
| `POST` base | Compute or retrieve one immutable comparison |
| `GET ?limit=10&offset=0` | Saved history, newest first |
| `GET /{analysis_id}` | Read one saved comparison belonging to this draft |

`limit` is 1–50 and `offset` is 0–100000. Valid slots: director, lead, co_lead, supporting_1, supporting_2, writer, cinematographer, composer. There is no generic `actor` slot.

The only accepted POST fields are:

```json
{
  "request_id": "e6ac5cf1-1a27-45dc-b260-acf43a19cb63",
  "slot": "director",
  "person_id": "946d42dc-938c-41c8-bec9-b6ea7967021e"
}
```

UUIDs above are illustrative. Use a person UUID returned for the actual film. No expected revision is required because the official film is unchanged. Seeds, scores, sample count, price, reserve and engine version cannot be supplied by clients.

The response contains `analysis_id`, `created_at`, `input_hash`, `output_hash` and `comparison`. The comparison includes source hashes, original/replacement cards, budget, score components, five metric distributions, changed relationship evidence and a reproducibility record containing the method, sample hash and 64 seeds. Decimal metric values are strings to preserve precision.

| Status | Meaning / response |
|---|---|
| 200 | Saved report or authorized read; repeated variants reuse the report |
| 401 | Missing, expired or revoked session; reauthenticate as owner |
| 404 | Draft/report absent or unavailable to this owner |
| 409 | Same request ID was already used with different contents |
| 422 | Film not successfully released, invalid role/person, duplicate person, over budget, extra fields or invalid pagination |
| 423 | Challenge has not closed; no lab data is disclosed |
| 503 | Database unavailable or source/report integrity check failed; preserve the exact request, resolve the underlying issue, then retry |

## Manual exact-request recovery in PowerShell

Save the UI's recovery object containing both `path` and `body` as `comparison-request.json`. This file must contain no token. Use a currently valid token for the same owner: restore the guest token, or sign in again through the account API and use its returned token. Swagger's Authorize control supports the same header.

```powershell
$privateToken = Read-Host 'Owning session token' -AsSecureString
$comparisonToken = [System.Net.NetworkCredential]::new('', $privateToken).Password
$comparisonRequest = Get-Content .\comparison-request.json -Raw | ConvertFrom-Json
$comparisonHeaders = @{ Authorization = 'Bearer ' + $comparisonToken }
Invoke-RestMethod -Method Post -Uri ('http://127.0.0.1:8001' + $comparisonRequest.path) -Headers $comparisonHeaders -ContentType 'application/json' -Body ($comparisonRequest.body | ConvertTo-Json -Depth 10)
Remove-Variable comparisonToken,comparisonHeaders,privateToken
```

Retain the original request ID and fields. A token is a credential: do not commit it or put it in the JSON recovery file. The server authorizes ownership before replay. An account claim makes the account token, rather than the revoked guest token, the valid credential.

Generated schemas are in `contracts/whatif-*.phase11.schema.json`; `contracts/openapi.current.json` documents the complete current API. Regenerate with `python -m scripts.export_phase11_contracts` from `backend/`. The older Phase 7/8 snapshot/result contracts remain unchanged.
