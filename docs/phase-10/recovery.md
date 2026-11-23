# Account and challenge recovery

The pending-request panel stores only an endpoint and body. Save its JSON as `recovery-request.local.json` if you must leave an uncertain operation. This filename is ignored by Git. Preserve its exact request ID, revision, offer, person and command.

For account-owned work, sign in again to the **same account** after expiry/refresh. You can load saved films or use **Resume my attempt** without creating another attempt. If the exact pending request is still in the tab, first use its retry control. If the session expired and that retry returns 401, the definite rejection clears the pending control; retain the JSON, sign out/clear the expired account and sign in again before inspecting or manually replaying the request.

A fresh account login authorizes the same ownership scope, so its new bearer token can replay the old request. Never save a password in the request file. Guest-owned work still requires the original valid recovery token; after a successful claim, use the owning account instead.

To replay a saved draft or challenge request manually in PowerShell at the project root, get a fresh account token through `/api/docs` **accounts/login**, using its credentials form, and keep it private. Or use the valid guest token for an unclaimed guest film:

```powershell
$request = Get-Content .\recovery-request.local.json -Raw | ConvertFrom-Json
$draftPath = '^/api/v1/drafts(?:/[0-9a-fA-F-]{36}/(?:picks|rerolls|recast/(?:preview|cancel|confirm)|finalize|abandon|release|retry-simulation))?$'
$challengePath = '^/api/v1/challenges/[a-z0-9][a-z0-9_-]{0,79}/attempts$'
if ($request.path -notmatch $draftPath -and $request.path -notmatch $challengePath) { throw 'Unexpected recovery endpoint.' }
$secret = Read-Host 'Valid owning bearer token' -AsSecureString
$token = [System.Net.NetworkCredential]::new('', $secret).Password
try {
    $headers = @{ Authorization = "Bearer $token" }
    $body = $request.body | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod -Method Post -Uri ('http://localhost:8001' + $request.path) -Headers $headers -ContentType 'application/json' -Body $body
} finally {
    Remove-Variable token, headers, secret -ErrorAction SilentlyContinue
}
```

If the command committed, its original receipt replays even after the deadline. If it did not commit and the window is now closed, a fresh action is rejected; recovery cannot backdate it. After replay, refresh the film to see current state. An older failed-release receipt can remain failed even after a later successful retry.

Authentication operations have their own recovery rules: uncertain registration → sign in with those credentials; uncertain password change → try the new password, then old if needed; uncertain guest claim → repeat the same proof on the same account. Do not repeat registration with different usernames to guess whether it worked. Logout clears the UI even if revocation could not be confirmed; password reset can revoke all remaining account sessions.

429 is a persistent sliding-window throttle, not a missing user. Wait for the window rather than changing IP headers. A 503 migration/database error requires fixing connectivity/schema before interpreting it as a missing draft. Never delete the volume to resolve an ownership or replay problem.
