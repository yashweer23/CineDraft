# Phase 8 change summary

Implemented the existing frozen baseline scoring/release specification for finalized Phase 7 drafts. Added Decimal arithmetic, independent SHA-256 random streams, reconciled fictional finances and four-week gross, immutable saved results, owner-authorized release/retry/status/result routes and a Release Report inside the existing draft inspector.

## Main files

| Area | Files |
|---|---|
| Pure scoring and release | `backend/app/simulation/engine.py` |
| Result/attempt contracts | `backend/app/simulation/schemas.py`, `contracts/result.phase8.schema.json` |
| Owner-authorized commands and reads | `backend/app/simulation/service.py`, `api.py` |
| Persistence | `backend/app/models.py`, new `backend/migrations/versions/0005_phase8.py` |
| Synthetic example | `backend/app/simulation/example.py`, `backend/scripts/simulation_example.py`, `data/phase8-simulation-example.json` |
| Saved replay verification | `backend/scripts/verify_release.py` and VS Code task |
| Studio | `frontend/src/ReleaseInspector.tsx`, `DraftInspector.tsx`, associated component tests |
| Backend checks | `test_simulation_engine.py`, `test_simulation_api.py`, `test_simulation_integration.py`, `test_simulation_concurrency.py` |

API/package version advances to 0.8.0. Current OpenAPI includes four new authenticated paths. Phase 7 inputs, config pins, token ownership and original request retry behavior are preserved. No dependency upgrade, new catalog build, live TMDB access, cloud deployment or background queue is required for the phase.

Observed: 258 unit checks, 30 frontend cases and 4 original-game cases passed; frontend build and static SQL/function syntax checks passed. All 64 PostgreSQL integration cases require local execution. The polished drafting and results interface is Phase 9.
