# Phase 6 — hands-on exercises

Start with the root README. Keep existing imported data and prices.

1. **Preview versus publish.** Preview with a new label; confirm `/api/collaboration/versions` has no new graph. Publish and refresh. Repeat the exact build: expect `created: false` and the same hash.
2. **Trace a connection.** Inspect every film page for one edge. Count distinct movie IDs and compare with `shared_movie_count`. Match both professional roles and jobs. Identify graph and dataset IDs in the response.
3. **Separate roles.** Compare a multi-role person's director and writer profiles against the same actor. Their evidence may differ. Zero overlap is valid. If your import lacks such profiles, use the synthetic example instead of assuming an overlap.
4. **Inspect the cap.** From a configured backend environment run `python -m scripts.graph_example`. Director/actor has six films and bonus 12, writer/actor one film and bonus 4 despite two jobs, and writer/composer zero. All six films remain in the first edge. The example is explicitly synthetic.
5. **Retain history.** Publish a second label from the same dataset. Both versions remain available and equivalent manifests can share a hash. Read the rollback/immutability tests; do not manually edit published rows.
6. **Read the algorithm.** Follow movie grouping, job deduplication, canonical pairs and bonus calculation. Predict the effect of a duplicate identical credit, then run the calculation tests.
7. **Read the transaction.** Find the advisory lock, dry-run return, inserts and seal. Read the migration's foreign keys and source-job validation, then run the real PostgreSQL suite locally.
8. **Record results.** Note migration head, suite results, graph ID/hash, idempotent rerun and one role-specific edge. Having a test file is not evidence of a successful run.

| File | Responsibility |
|---|---|
| `backend/app/collaboration/calculation.py` | Pure grouping, identity, deduplication, bonus, reports/hashes |
| `backend/app/collaboration/service.py` | Dataset loading and atomic publication |
| `backend/app/collaboration/api.py` / `schemas.py` | Routes, response models and pagination |
| `backend/migrations/versions/0003_phase6.py` | PostgreSQL schema/guards |
| `frontend/src/CollaborationLab.tsx` | Version browsing, pair selection and film evidence |
| `backend/tests/test_collaboration_*.py` | Algorithm, API and real database verification |

After publishing, formula experiments need a new algorithm version and label, an updated bonus constraint in a **new migration**, and continued read support for historical versions. Changing one constant alone conflicts with frozen output and database invariants.
