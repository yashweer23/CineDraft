# API contracts — Phase 3

**Implemented runtime:** `GET /api/health`, `GET /api/health/ready`, `/api/docs`, `/api/openapi.json`. Health version is 0.3.0. Readiness checks connectivity only, not the migration head.

**Proposed game API:** `contracts/openapi.proposed.json`, generated from Pydantic models in `backend/app/contracts.py`. No `/api/v1` game route is mounted. Calling one now returns 404. Every exported operation carries `x-implementation-status: planned`. `contracts/schemas.json` contains reusable JSON schemas. OpenAPI is an API definition, not an implemented backend.

## Endpoint map

| Proposed endpoint | Input / response | Planned behavior |
|---|---|---|
| `GET /api/v1/catalog/genres` | Genre list | Catalog genres |
| `GET /api/v1/catalog/candidates` | Version IDs, role, genre, cursor, limit 1–50 / CatalogPage | Stable version-scoped role cards |
| `GET /api/v1/catalog/people/{person_id}` | Version IDs, role, genre / CandidateCard | Role-specific details and up to five notable films |
| `POST /api/v1/drafts` | CreateDraftRequest / DraftView, 201 | Preflight, freeze versions, first offer |
| `GET /api/v1/drafts/{draft_id}` | DraftView | Authorized recovery of persisted state |
| `POST .../picks` | PickRequest / DraftView | Choose a candidate from current offer |
| `POST .../rerolls` | RerollRequest / DraftView | Change current hand once |
| `POST .../recast/preview` | RecastPreviewRequest / DraftView | Cache alternatives for filled slot |
| `POST .../recast/cancel` | RecastCancelRequest / DraftView | Keep original roster and allowance |
| `POST .../recast/confirm` | RecastConfirmRequest / DraftView | Replace once, atomically refund old fee |
| `POST .../finalize` | MutationRequest / DraftView | Validate all eight slots and freeze inputs |
| `POST .../release` | MutationRequest / DraftView, 202 | Start one simulation identity |
| `POST .../retry-simulation` | MutationRequest / DraftView, 202 | Reuse frozen inputs/seed/identity |
| `POST .../abandon` | MutationRequest / DraftView | Confirmed termination; preserve records |
| `GET .../result` | ResultView | Return saved explainable result |

Here `...` means `/api/v1/drafts/{draft_id}`. Catalog wire definitions are preparatory; ingestion arrives in Phase 4, computed features/ranking/prices in Phase 5, and player actions in Phase 7. Results depend on Phase 8. There are 15 distinct proposed paths.

## Requests and ownership

Creation accepts only `request_id`, `genre_id`, `tier`, `mode=classic`. Mutations require `request_id` (UUID) and `expected_revision` (non-negative strict integer), with offer/person/slot fields appropriate to the action. Extra request fields are rejected. Clients do not choose authoritative fees, seeds, remaining budgets or data versions.

All draft routes declare bearer authentication in the proposed spec. Implement a verified user/guest capability before mounting any route. A draft UUID is not proof of ownership. Check ownership before state reads, idempotent replay or mutation; use 404 for drafts inaccessible to the caller, preventing ownership enumeration. Missing/invalid credentials return 401. Do not put raw capability tokens into response snapshots, logs or action records.

## Transaction and idempotency requirements

Future engine transaction order:

1. Authenticate; authorize ownership; lock the draft row.
2. Look up `(draft_id, command_type, request_id)` **before** checking the revision. Same canonical request body returns its stored status/body, even if the current draft has advanced. A changed body with the same key returns 409 `idempotency_conflict`.
3. Compare `expected_revision`. If stale, return 409 `stale_revision` with the current authorized revision and instruct the client to fetch state. Do not mutate or consume allowance.
4. Validate legal state, current offer, person identity, role, budget and exact feasible completion.
5. Persist all effects, new offers, revision+1 and the successful request/response together. Commit once. Retry deadlocks/serialization failures with bounded server policy, preserving the original request identity.

`repository.replay_action` only looks up/verifies a stored response; it is not the complete transaction engine. Creation has no draft ID yet: its future idempotency scope must be `(verified_owner, create, request_id)`, backed by a dedicated creation-request record/unique constraint when the creation service is implemented. Do not use a fresh generated draft ID as its idempotency scope. That owner-scoped creation ledger is deliberately pending with Phase 7, and must be added before exposing POST /drafts.

Only successful commands are saved in `action_records`. Validation/stale failures do not consume a revision or reroll. Recast preview and cancel are state mutations; each advances revision but never changes fees or allowances. Reopening a slot reuses its cached choices, with response revision reflecting current state.

## Legal transitions

| State | Allowed future action | Result |
|---|---|---|
| awaiting_pick | pick / reroll | awaiting_pick, or recast_available after pick 8 |
| recast_available | preview | recast_preview; roster unchanged |
| recast_preview | cancel / confirm | recast_available / review_locked |
| recast_available, review_locked | finalize | production_finalized |
| production_finalized | release | simulation_running |
| simulation_running | internal success / failure | results_available / simulation_failed |
| simulation_failed | retry-simulation | simulation_running with same frozen inputs |
| Unfinished drafting/review states | confirmed abandon | abandoned |

Abandon is not permitted during/after finalized production or for a completed result. The current state service is not implemented. Internal simulation completion/failure events and job bookkeeping will need their own transactional records in Phase 8; they are not client commands. Refer to [the detailed Phase 1 state specification](../phase-01/game-state-and-edge-cases.md).

## Data and errors

Money is integer USD with a JavaScript-safe integer maximum in wire schemas. Source audience ratings remain nullable and separate from fictional game attributes. Candidate cards carry role, fictional fee flag, coverage, specialties, versions and 0–5 distinct role-specific works. Empty filmographies are not fabricated. Disabled choices have a reason; short offers have a shortage message. Pick offers require at least one selectable candidate; an empty recast preview may explain that no alternative exists.

`FrozenInputs` requires eight unique slots/people, matching fees/versions, no current offer and finalized state. It retains exact displayed attributes/works, seed, rules and scoring configuration. The repository checks persisted roster/version consistency before saving. `ResultView` validates score ranges, profit reconciliation and a four-week total matching gross; it permits a financial loss.

Error envelope:

```json
{
  "error": {"code": "stale_revision", "message": "Reload the current draft.", "current_revision": 5},
  "request_id": "00000000-0000-4000-8000-000000000001"
}
```

The illustrated request ID is a synthetic shape example. Standard statuses: 401 authentication, 404 inaccessible/missing record, 409 revision/idempotency/state conflict, 422 invalid fields or illegal choice, 503 unavailable infrastructure/catalog. Error bodies must not leak credentials or another owner's state. Future error codes include `invalid_transition`, `candidate_not_offered`, `duplicate_person`, `insufficient_budget`, `no_feasible_completion`, `rerolls_exhausted`, `recast_used`, `catalog_unavailable` and `simulation_pending`.
