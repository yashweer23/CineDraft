# Live raw catalog API

Open `/api/docs` on the running API. `contracts/openapi.current.json` is the checked-in export of the live Phase 4 routes. It is separate from `openapi.proposed.json`, which still describes future game behavior and is not mounted.

| Method and path | Result |
|---|---|
| `GET /api/health` | API liveness |
| `GET /api/health/ready` | PostgreSQL `SELECT 1` connectivity |
| `GET /api/catalog/attribution` | TMDB attribution notice and links; no DB required |
| `GET /api/catalog/datasets` | Sealed versions and coverage reports |
| `GET /api/catalog/{dataset_id}/movies` | Imported movie facts; eligible by default |
| `GET /api/catalog/{dataset_id}/people` | People with a mapped credit on an eligible imported movie |
| `GET /api/catalog/{dataset_id}/people/{person_id}/films` | Eligible films for one person and one required role |

All lists accept `limit` from 1–50 (default 20) and `offset` from 0–100000 (default 0). `next_offset` is null when there are no further results. Use it rather than assuming every page is full. Dataset order is by ID; movies/people by UUID; person films by release date descending then movie UUID. Concurrent publication may shift dataset-list offsets; within a sealed dataset rows are fixed.

Movies accept `eligibility=eligible|excluded|review|all`. People optionally accept `role=actor|director|writer|cinematographer|composer`. The same role is required for a person's film list. One person can appear for multiple roles but keeps the same UUID.

Use `/api/catalog/datasets` to discover the exact dataset ID, such as `tmdb:first-import-v1`, and the people endpoint to discover actual UUIDs. Do not put a numeric TMDB ID into a `person_id` UUID path. Provider IDs are returned separately as `source_key` with `source`. The synthetic Phase 3 fixture has its own `fixture:` namespace.

Filmography returns raw `audience_rating`, vote count, title, release date, runtime, poster URL, eligibility and `credited_jobs`. Ratings are TMDB audience values on a 0–10 scale, not game talent ratings. `ranked_notable_works` is explicitly false. The list is limited to movies in this import, not the person's complete career, and it is not a top-five ranking.

Nullable source fields remain null. Clients should show “Not available” and image placeholders where needed. No fictional fee, game skill score, generated review or fabricated movie metadata is returned. Dataset entries explicitly set `playable: false`.

A missing/unsealed dataset or unknown person returns 404; invalid parameters return 422; database/migration failures return a sanitized 503. Errors follow the existing `{error: {code, message}, request_id}` envelope and `X-Request-ID` header. Health readiness does not assert that migrations or imports are complete.

## Try it in PowerShell

After publishing the README's first import:

```powershell
$api = 'http://localhost:8000' # use your configured API_PORT
Invoke-RestMethod "$api/api/catalog/datasets" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$api/api/catalog/tmdb:first-import-v1/movies?limit=5" | ConvertTo-Json -Depth 8
Invoke-RestMethod "$api/api/catalog/tmdb:first-import-v1/people?role=director&limit=5" | ConvertTo-Json -Depth 8
```

Select an actual returned person UUID in Swagger for the final endpoint. No browser request needs a TMDB credential. `api.http` contains equivalent editable requests for a VS Code REST client extension, if you use one.
