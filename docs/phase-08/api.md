# Phase 8 API

Base URL on your machine: `http://localhost:8001/api/v1`. The frontend uses relative `/api/v1` through Vite. All four new routes require the same guest bearer token that owns the draft. Knowing a draft UUID, request ID or simulation ID grants no access.

| Method / path | Request | Response |
|---|---|---|
| `POST /drafts/{id}/release` | `request_id`, `expected_revision` | Saved command receipt containing `draft` and `attempt` |
| `POST /drafts/{id}/retry-simulation` | `request_id`, `expected_revision` | New retry receipt after a confirmed simulation failure |
| `GET /drafts/{id}/simulation` | No body | Current state, latest attempt, result availability |
| `GET /drafts/{id}/result` | No body | Immutable `{output_hash, result}` |

The full running schema is `/api/openapi.json`; interactive docs are `/api/docs`. `contracts/openapi.current.json` includes 33 paths. Historical proposed contracts are not the current route inventory.

## PowerShell exercise

Restore your existing owner token without echoing it:

```powershell
$api = 'http://localhost:8001/api/v1'
$secureToken = Read-Host 'Your recovery token' -AsSecureString
$ownerToken = [System.Net.NetworkCredential]::new('', $secureToken).Password
$headers = @{ Authorization = "Bearer $ownerToken" }
$draftId = 'PASTE-YOUR-DRAFT-UUID'
$draft = Invoke-RestMethod "$api/drafts/$draftId" -Headers $headers
```

The draft must be `production_finalized`. Its eight picks, graph evidence, prices, rules and scoring inputs have already been frozen. Construct a release request once:

```powershell
$releaseBody = @{
    request_id = [guid]::NewGuid().ToString()
    expected_revision = $draft.revision
} | ConvertTo-Json
$receipt = Invoke-RestMethod -Method Post "$api/drafts/$draftId/release" -Headers $headers -ContentType 'application/json' -Body $releaseBody
$receipt.draft | Select-Object draft_id, status, revision
$receipt.attempt | Select-Object attempt_number, status, error_code, message
```

For a successful computation, expect `results_available` and a `succeeded` attempt. Read the result:

```powershell
$saved = Invoke-RestMethod "$api/drafts/$draftId/result" -Headers $headers
$saved.result | Select-Object studio_score, critics, audience, worldwide_gross_usd, studio_receipts_usd, profit_usd
$saved.result.score_components | Format-Table
$saved.result.weekly_gross_usd
$saved.output_hash
```

A result read cannot trigger a simulation. It verifies the stored output hash and schema before returning. No result yet gives `404 result_not_available`; another owner's draft gives `404 draft_not_found`.

## Duplicate requests and confirmed failures

Replay the exact release request:

```powershell
$again = Invoke-RestMethod -Method Post "$api/drafts/$draftId/release" -Headers $headers -ContentType 'application/json' -Body $releaseBody
$again.attempt.attempt_id -eq $receipt.attempt.attempt_id
```

Expected: `True`. No new attempt, charge or revision is created. Keep `$releaseBody` until the outcome is known. A timeout or 5xx does not prove that the transaction failed to commit.

If the receipt explicitly reports `simulation_failed`, the computation failure is durable and no result exists. Inspect the API logs for the error type and fix the cause. Then read the current draft and construct a **new** retry command:

```powershell
$draft = Invoke-RestMethod "$api/drafts/$draftId" -Headers $headers
$retryBody = @{
    request_id = [guid]::NewGuid().ToString()
    expected_revision = $draft.revision
} | ConvertTo-Json
$retried = Invoke-RestMethod -Method Post "$api/drafts/$draftId/retry-simulation" -Headers $headers -ContentType 'application/json' -Body $retryBody
```

This does not reseed the film. If that retry's response is interrupted, retry the same `$retryBody` and URL. A successful film cannot be retried as a new command. Replaying an older failed receipt remains allowed for its owner, but returns that original failure, not the later successful state; GET returns current state.

## Errors and invariants

| Response | Meaning |
|---|---|
| 401 `invalid_session` | Token missing, malformed, unknown, expired or revoked |
| 404 `draft_not_found` | This session has no access to the requested draft |
| 404 `result_not_available` | No successful result exists for the owned draft |
| 409 `stale_revision` | Refresh current state before choosing a new action |
| 409 `idempotency_conflict` | This command ID already belongs to different fields |
| 409 `invalid_release_state` | Release/retry is invalid for the current state |
| 422 `validation_error` | Invalid or extra client fields, including seed, noise, scores, iterations or version overrides |
| 422 `unsupported_simulation_input` | Unsupported or inconsistent frozen inputs; no attempt committed |
| 503 `database_unavailable` | Database operation or commit acknowledgment failed; exact retry is safe |
| 503 `result_integrity_error` | Saved output hash/schema/identity verification failed; history was preserved |

A **confirmed engine failure** is HTTP 200 with `attempt.status: failed` and `draft.status: simulation_failed`. HTTP 200 means the command receipt was committed, not that a result was produced. The UI checks the state explicitly.

Private responses use `Cache-Control: no-store`. The diagnostic `X-Request-ID` identifies a particular HTTP request; the JSON `request_id` you supply identifies the idempotent game command. They serve different purposes.

## Precision and evidence

Precision-bearing fields such as score components, unrounded reviews, noise, retention and return are decimal strings. Integer-dollar outputs remain JSON integers; displayed reviews are numbers rounded to two decimals. Read full precision from the saved result rather than trying to reconstruct it from formatted UI values.

The result records source versions and the full reproducibility manifest. Chemistry links use the result's pinned `graph_id` and `edge_id`; they never use the latest active graph. Exact credited jobs refer to canonical graph endpoints, which the UI maps back to the selected people. Shared evidence is not a claim of personal friendship or compatibility.

The owner receives the frozen seed in the saved result after release. No guest token, DB credential or TMDB credential is included.
