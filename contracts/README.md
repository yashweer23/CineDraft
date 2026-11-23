# Current and historical contracts

`openapi.current.json` describes the implemented 0.10.0 API: health, raw catalog, computed talent, collaboration graph, guest/account sessions, drafting, release simulation and daily challenges. Generate it from `backend/` with `python -m scripts.export_phase10_contracts`. The live specification is `/api/openapi.json`; Swagger is `/api/docs`.

`result.phase8.schema.json` describes immutable `phase8-v1` result JSON, including exact decimal strings, fictional finances, score explanation and reproducibility metadata. Generate it with `python -m scripts.export_simulation_contracts`.

`snapshot.phase7.schema.json` describes frozen `phase7-v1` production inputs, including selected role features, graph evidence and version pins. Its schema remains unchanged in Phase 8. The engine consumes these snapshots without rewriting them.

`openapi.proposed.json` and `schemas.json` preserve the historical Phase 3 design and `phase3-v1` models. Their `planned` labels are historical, not a current route inventory. Old synthetic fixture results remain supported by existing helpers; they are not relabeled as Phase 8 engine output.

The four new authenticated paths are POST release/retry-simulation and GET simulation/result under `/api/v1/drafts/{draft_id}`. See [the Phase 8 API guide](../docs/phase-08/api.md) for response shapes and the difference between a duplicate request and a new retry after confirmed failure.

Phase 9 adds authenticated `GET /api/v1/drafts/{draft_id}/roster`: `{draft_id, revision, members}`, where each member contains `slot`, `locked_fee_usd` and the saved `LiveCard`. `LiveDraft`, the Phase 7 snapshot schema and Phase 8 result schema remain unchanged.

Phase 10 adds account registration/session/claim/password routes and immutable challenge definitions, attempts, rankings, audit and owner context. See [the Phase 10 API guide](../docs/phase-10/api.md). The added `account-registration.phase10.schema.json`, `challenge.phase10.schema.json` and `leaderboard.phase10.schema.json` accompany current OpenAPI. Official scores are server-generated; there is no score-upload endpoint.
