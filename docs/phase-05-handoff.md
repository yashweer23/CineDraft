# Phase 5 — ratings, fictional prices and notable works

Continue with Phase 5 only. Preserve the cumulative VS Code ZIP workflow, original prototype, studio health flow and immutable schema history. Do not publish a hosted site or request credentials in chat.

## Starting state

Phase 4 implements backend-only TMDB requests, resumable checkpoints, reviewed scope/credit mapping, sealed publication and raw catalog routes. Read `docs/phase-04/verification.md`: real PostgreSQL and authenticated TMDB execution were not verified in the delivery environment. Require actual local/CI evidence before claiming those gates passed. Do not erase these limits from the history.

Inspect the Phase 1 data/scoring specifications, Phase 3 schema/contracts, Phase 4 importer and current raw API. Existing feature_versions, role_features, pricing_versions and role_prices are the versioned targets for this phase. Never rewrite migrations 0001 or 0002 after application; add a new revision if required.

## Implement

1. An explicit, repeatable feature-building command consuming a sealed dataset. Specify deterministic formulas, shrinkage/prior behavior for sparse evidence, null handling, cutoffs and source coverage. Use only eligible movies and exact mapped credits for each role. Do not treat imported coverage as a complete career.
2. Role-specific talent features and genre fit with documented inputs and auditable contributions. One person can have different role profiles without duplicate identity. Preserve source audience rating separately from game scores.
3. Fictional hiring fees represented as integer US dollars. Document calibration and version all parameters. Clearly label game fees as fictional; never describe them as real salaries or market rates.
4. Ranked notable works: up to five real imported eligible films for the exact role, with genuine source artwork/metadata, stable tie-breaking, evidence/coverage explanations and no invented filler. A chronological list must not be relabeled as ranked without a ranking algorithm.
5. Atomic sealed feature/pricing publication, checksums/manifests, provenance, safe reruns and old-version preservation. Avoid network requests in feature generation or gameplay reads.
6. Implemented read-only output contracts for these results. Keep current vs proposed OpenAPI exports explicit and do not mount planned write/game routes.
7. Meaningful unit tests for sparse/null evidence, multi-role people, tie-breaking and exact money; PostgreSQL integration checks for publication rollback, repeat runs and snapshot immutability. Report executed vs skipped checks honestly.
8. Hands-on exercises, calibration examples using clearly labeled synthetic data, setup commands, a verification report and Phase 6 handoff. Deliver a new cumulative ZIP with all earlier source/docs.

## Boundaries

Do not promise playable pools just from role counts or computed prices. Exact assignment feasibility, ownership and transactional actions are Phase 7. Phase 6 builds collaboration features; Phase 8 simulates results; Phase 9 completes the game interface. Do not mutate imported movie facts to make calibration pass. If the sample is too small, explain its coverage and use a new explicit import version.
