# Recover an interrupted command

Use **Retry same request** while the tab is still open. It sends the same endpoint, bearer token, request ID and JSON body. Do not generate a new request ID to guess whether the server committed.

When the response is known but the subsequent draft/roster GET fails, use **Refresh draft**. The guided studio differentiates these two cases. A historical receipt can describe an older state, so read current state after replay.

## If you must close the tab

Privately save the token and the JSON under **Keep this request for recovery**. Save the JSON to `recovery-request.local.json` in the project root (ignored by Git). It contains `path` and `body`, not the token. Do not edit its ID, revision, offer, person or command.

After restarting the API, replay it from PowerShell at the project root. This example is for the new guided studio's `/api/v1/...` request format:

```powershell
$request = Get-Content .\recovery-request.local.json -Raw | ConvertFrom-Json
$allowedPath = '^/api/v1/drafts(?:/[0-9a-fA-F-]{36}/(?:picks|rerolls|recast/(?:preview|cancel|confirm)|finalize|abandon|release|retry-simulation))?$'
if ($request.path -notmatch $allowedPath) { throw 'Unexpected recovery endpoint. Do not replay it.' }
$secret = Read-Host 'Owning recovery token' -AsSecureString
$token = [System.Net.NetworkCredential]::new('', $secret).Password
try {
  $headers = @{ Authorization = "Bearer $token" }
  $body = $request.body | ConvertTo-Json -Depth 20 -Compress
  Invoke-RestMethod -Method Post -Uri ('http://localhost:8001' + $request.path) -Headers $headers -ContentType 'application/json' -Body $body
} finally {
  Remove-Variable token, headers, secret -ErrorAction SilentlyContinue
}
```

The response is the original receipt if that command already committed. It does not change its ID to a new command. A receipt may describe an earlier revision or an earlier failed simulation. Restore your session in the studio, open **Session & saved films**, and open the film to load current state.

A 401 means the token is invalid, revoked or expired; creating another token does not grant access. A 409 can indicate altered request fields, stale revision or an invalid action. Inspect the structured response and refresh current state; do not edit persisted snapshots or erase the database to recover.

If you lost both the pending JSON and its response, restore the token and inspect current server state before any new action. The UI cannot reconstruct the original command ID from memory after reload. The database still retains committed history; this phase does not add a receipt-search UI or lost-token recovery.
