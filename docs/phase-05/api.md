# Phase 5 API and atomic publication

The running `/api/docs` and checked-in `contracts/openapi.current.json` describe implemented health, raw catalog and talent endpoints. Future `/api/v1` game routes remain only in `openapi.proposed.json` and are not mounted.

| GET endpoint | Purpose |
|---|---|
| `/api/talent/versions` | Computed, sealed Phase 5 feature/pricing versions; optional `dataset_id` filter |
| `/api/talent/{pricing_id}/profiles` | Cards for a required `role` and optional `genre` (default drama) |
| `/api/talent/{pricing_id}/profiles/{person_id}/{role}` | One card plus film evidence, parameters and exact pricing explanation |
| `/api/talent/{pricing_id}/report` | Feature coverage, catalog gaps, fee ranges and budget diagnostics |

Lists accept `limit=1..50` and `offset=0..100000`, returning `next_offset` or null. Versions sort by pricing ID. Profiles sort by stored talent strength descending then stable person UUID. Cards are paginated, with at most five notable movies per card. The API batches movie reads per page; it does not issue a TMDB request or recompute the feature build on each read.

A version pins its dataset, feature/pricing hashes, role mapping and ranking rules. Pass a real internal UUID from a returned card to the detail route. Provider `source_key` is separate from that UUID. The Phase 3 handwritten fixture versions are intentionally absent from the computed-version list; build a new Phase 5 version from their dataset to see computed synthetic profiles.

Each card contains fictional integer USD fee, strength/reception/experience/versatility, optional popularity percentile, selected-genre fit/evidence count/gap flag, specialties, career span, coverage and ranked works. Every work includes source identity, title, source-supported year/image/rating, exact matching jobs and ranking component weights. Source ratings remain nullable and 0–10; game attributes use 0–100.

Detail evidence lists all contributing movie IDs, rated movies and adjusted reception contributions; genre counts/priors; ranked movie IDs; strength contributions; and the frozen parameters. Its pricing explanation is reproduced from the stored features using the pinned supported formula and checked against the stored integer fee. A mismatch returns 503. No version is advertised as playable.

Missing/unpublished/unsupported versions or absent role profiles return 404, invalid role/genre/UUID/pagination returns 422, and database failures return a sanitized 503. Existing error envelopes and request IDs remain in use. These are local read-only development APIs; draft ownership and authorized mutations are Phase 7.

## Publication and hashes

`python -m scripts.build_talent --dataset ID --version LABEL` uses one transaction and a PostgreSQL advisory transaction lock. It reads sealed source data, computes features and prices, writes/seals the feature version, then writes/seals its pricing version. Both become visible on one commit; a pricing failure rolls the new features back too. Existing versions are not updated or removed.

The feature manifest includes the dataset manifest hash, hash of normalized calculation inputs, hash of complete role-profile outputs, formula parameters, mapping/scope versions and coverage report. The pricing manifest includes the feature manifest hash, parameters, hash of price rows/explanations and pricing report. Row order is canonical; duplicate identical jobs do not change mathematical inputs. `content_hash` continues to mean the hash of the manifest, whose row checksums bind the computed content.

A rerun calculates expected manifests and returns `created: false` only when both existing sealed versions match. Different inputs, changed parameters or partial output under the same label are rejected. Dry-run performs the calculations/conflict checks without inserts. Source reads and calculations are offline relative to TMDB.

## PowerShell requests

```powershell
$api = 'http://localhost:8001' # use your API_PORT
Invoke-RestMethod "$api/api/talent/versions" | ConvertTo-Json -Depth 8
Invoke-RestMethod "$api/api/talent/pricing:first-ratings-v1/profiles?role=director&genre=crime&limit=3" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$api/api/talent/pricing:first-ratings-v1/report" | ConvertTo-Json -Depth 12
```

See `api.http` for equivalent optional VS Code REST Client requests. The studio's Talent Lab uses these same endpoints through the Vite proxy.
