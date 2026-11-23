# Phase 6 API

All graph routes are read-only, local and version-pinned. They make no TMDB requests or graph recomputations. Swagger is at `http://localhost:8001/api/docs`; `contracts/openapi.current.json` describes the actual implementation. Game mutation routes remain unmounted.

| GET endpoint | Parameters / result |
|---|---|
| `/api/collaboration/versions` | Optional `dataset_id`; published supported versions and report counts |
| `/api/collaboration/{graph_id}/nodes` | Optional `role`, literal case-insensitive name search `q` (max 80 characters); includes isolated nodes |
| `/api/collaboration/{graph_id}/edges` | Optional `role`, `person_id`; shared count descending with stable edge-ID ties |
| `/api/collaboration/{graph_id}/pair` | Required `person_a`, `role_a`, `person_b`, `role_b`; canonical pair or explicit zero-evidence result |
| `/api/collaboration/{graph_id}/edges/{edge_id}/films` | Paginated movie/job evidence |
| `/api/collaboration/{graph_id}/report` | Version, parameters and dataset/input/output hashes |

Lists accept `limit=1..50` and `offset=0..1000000`, default limit 20. Follow `next_offset` until null. Nodes sort by UUID/role, versions by graph ID, evidence by movie UUID. When filtering edges by both person and role, the **same endpoint** must satisfy both filters. Use internal UUIDs returned by `/nodes`, not names or TMDB numeric `source_key` values.

Edges contain `a` and `b` (identity, name, role, source, film count), `shared_movie_count`, integer `bonus`, and `capped`. Positive edges have a 64-character ID. A valid pair without overlap returns 200, `edge_id: null`, zero count/bonus and the documented absence message. Reversing request order preserves the canonical view.

Missing/unpublished/unsupported versions, nonexistent edges and missing role nodes return 404. Invalid roles, UUIDs, IDs, bounds and self-pairs return 422. Database or missing-migration errors return sanitized 503. Existing request IDs/error envelopes remain. Graphs are not marked playable.

## PowerShell examples

```powershell
$api = 'http://localhost:8001'
$graph = 'graph:first-graph-v1'
Invoke-RestMethod "$api/api/collaboration/versions" | ConvertTo-Json -Depth 8
Invoke-RestMethod "$api/api/collaboration/$graph/nodes?role=director&limit=10" | ConvertTo-Json -Depth 8
$edges = Invoke-RestMethod "$api/api/collaboration/$graph/edges?limit=5"
$edges | ConvertTo-Json -Depth 8
```

Only if the returned page contains an edge:

```powershell
$edge = $edges.items[0]
$edgeId = $edge.edge_id
Invoke-RestMethod "$api/api/collaboration/$graph/edges/$edgeId/films?limit=50" | ConvertTo-Json -Depth 10
$a = $edge.a.person_id
$roleA = $edge.a.role
$b = $edge.b.person_id
$roleB = $edge.b.role
Invoke-RestMethod "$api/api/collaboration/$graph/pair?person_a=$a&role_a=$roleA&person_b=$b&role_b=$roleB" | ConvertTo-Json -Depth 8
```

Movie evidence keeps nullable year/poster fields and exact jobs on both sides. Real records link to TMDB; synthetic records have no fabricated source URL. List routes batch related node/movie reads and paginate evidence rather than embedding unlimited films in every card.
