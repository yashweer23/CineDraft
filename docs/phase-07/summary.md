# Phase 7 change summary

Implemented classic drafting over the existing sealed catalog, ratings, prices and graph. Added exact distinct-person assignment feasibility, server-generated persisted offers, owner-scoped guest capabilities, transactional actions with optimistic revisions and idempotent receipts, two rerolls, cached optional recast and immutable production inputs.

## Main files

| Area | Files |
|---|---|
| Exact assignment and deterministic offer rules | `backend/app/drafting/assignment.py`, `rules.py` |
| Compatible catalog preparation | `backend/app/drafting/catalog.py`, `backend/scripts/prepare_drafting.py` |
| Ownership and transactions | `backend/app/drafting/auth.py`, `service.py`, `api.py`, `errors.py` |
| Current/frozen contracts | `backend/app/drafting/schemas.py`, `contracts/openapi.current.json`, `contracts/snapshot.phase7.schema.json` |
| Persistence | `backend/app/models.py`, `repository.py`, new `backend/migrations/versions/0004_phase7.py` |
| Studio inspector | `frontend/src/DraftInspector.tsx`, its component tests, `App.tsx` |
| Backend tests | `test_draft_assignment.py`, `test_draft_api.py`, `test_draft_snapshot.py`, `test_draft_integration.py`, `test_draft_concurrency.py` |
| Hands-on example | `backend/scripts/assignment_example.py`, `data/phase7-assignment-example.json` |

VS Code tasks include catalog preview/activation prompts and start the native frontend on your port 5174.

The API and package version advance to 0.7.0. Frontend dependency versions stay locked. Legacy proposed contracts and old snapshot schemas remain intact. Full game UI is still Phase 9; the inspector exposes the engine for learning and testing now.

Verification observed: 200 backend checks passed; 52 PostgreSQL cases skipped; 22 frontend checks and 4 original-game cases passed; frontend build and static migration syntax passed. See [verification](verification.md) for the remaining gates. No new real-data or runtime database success is claimed.
