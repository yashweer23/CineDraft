# Phase 7 — authoritative drafting and budget feasibility

Continue with Phase 7 only and the cumulative VS Code ZIP workflow. Do not deploy a site. Preserve private environment files, host ports 5433/8001/5174, original game assets, sealed datasets/ratings/prices/graphs, draft history and historical migrations.

## Inspect first

Read Phase 1 game/domain/scoring/API specs, Phase 3 persistence, Phase 4 import scope, Phase 5 formulas and Phase 6 graph design/API/verification. Migration head is `0003_phase6`. Old draft snapshots have no graph version; introduce new graph pins through a new migration/versioned contract without rewriting history.

The user reported Phase 5's 22 PostgreSQL tests passing. Phase 6's 37 PostgreSQL tests were not executed in the packaging environment. Run the full real suite before claiming those gates passed. Fee balance and large-catalog graph performance remain unproven.

## Implement

1. Server-authoritative draft creation, ownership and authorized actions aligned with the existing domain states/proposed contracts. Define token handling and invalid/expired access; keep secrets out of browser bundles and logs.
2. Pin compatible sealed dataset, features, prices, graph and rules for each new draft. Preserve replay of old snapshots; never silently upgrade draft inputs.
3. Exact unique-person assignment feasibility across eight slots and integer USD fees. Multi-role people cannot occupy several slots. Summed minima alone do not prove a feasible complete roster.
4. Enable budget tiers and generate offers only when a valid completion exists. Lock fees to the pinned pricing version and enforce reserve, slot order, reroll and recast rules. No implicit rescue discounts.
5. Deterministic server-controlled offers/random streams, optimistic revisions and idempotent actions. Transactions must validate ownership, expected revision, offer membership, budget and state before recording changes. Never trust client fees, roles, eligibility or scores.
6. Defined reroll/recast/finalization flows and immutable final inputs. Preserve completed results and the original prototype. Simulation remains Phase 8.
7. Tests for affordable-but-impossible assignment, multi-role collisions, unauthorized actions, duplicate/stale requests, concurrent picks, rollback, version mismatch and deterministic replay. Run migration drift and PostgreSQL checks locally/CI.
8. Updated current OpenAPI, setup, hands-on exercises, verification and Phase 8 handoff. A developer draft inspector is enough; complete game UI belongs to Phase 9.

## Graph boundary

Phase 6 stores all role-pair evidence; future chemistry must use the twelve designated roster relationships rather than summing all edges. No shared credits is neutral absence, not incompatibility. Keep source evidence pinned to each draft's graph and dataset.
