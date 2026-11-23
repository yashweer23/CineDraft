# Phase 6 verification — 24 October 2026

| Check | Result in packaging environment |
|---|---|
| Backend suite | **141 passed; 37 PostgreSQL integration tests skipped** |
| Frontend suite | **14 passed** |
| TypeScript / production build | Passed |
| Original-game suite | **4 passed** |
| Graph CLI help | Passed |
| Database-free synthetic graph example | Executed; deterministic saved JSON matches calculation; six/one/zero-film examples yield 12/4/0 |
| Current OpenAPI | Regenerated; exact contract equality test passed; 17 implemented GET paths, including six collaboration paths |
| Alembic SQL generation | Phase 6 upgrade generated successfully from `0002_phase4` |
| PostgreSQL static syntax checks | 19 generated statements and all three new PL/pgSQL functions parsed successfully |
| Docker / PostgreSQL runtime | Unavailable here; migration execution, drift comparison and integration behavior require local/CI verification |
| Live TMDB calls | Not run; graph builds use sealed local data |
| Browser visual inspection | Not performed; component tests/build are not visual or full-stack verification |

The 27 new backend unit/API cases cover canonical orientation, role separation, deduplication, complete capped evidence, isolated nodes, hash stability/change, invalid source identities/references/roles/jobs, resource bounds and request contracts. Existing tests caught and prompted correction of duplicate foreign-key names on the two graph endpoints before packaging.

Fifteen new PostgreSQL cases join the earlier 22. They cover publication/idempotency, preserved history, dry-run/conflicts, forced insert rollback, eight update/delete rejection cases, self-edges/wrong jobs/incomplete sealing, actual API roles/evidence/pagination, valid zero-overlap pairs, and downgrade/re-upgrade with earlier data preserved. They are present but **were not executed here**. Static SQL parsing cannot prove trigger behavior or migration correctness against a running database.

Seven new frontend cases cover empty catalog, exact source roles/jobs, all evidence pages past the cap, missing-year labeling, pair comparison/self-selection prevention, filters/name search, API/evidence retry and clearing evidence when graph versions change. Existing seven cases still pass. Test data is explicitly synthetic.

The user's earlier report of 114 unit tests, 22 database tests, four original-game tests and a connected frontend/API/database remains Phase 5 evidence. It does not establish that Phase 6's new migration and 37 database cases passed on their machine.

## Required local checks

Follow the root README to rebuild, run `alembic upgrade head` and confirm **`0003_phase6`**, then:

```powershell
docker compose --profile verification run --rm --build api-tests
npm run check:stack
```

Expected database result: **37 passed**, unrelated unit cases deselected. Existing CI also runs the entire backend suite against PostgreSQL 17; it has not been executed remotely for this delivery.

Preview and publish a graph from your sealed dataset, compare an actual role-specific pair, inspect all evidence pages, repeat the build to verify `created: false`, and check both old/new graph versions remain accessible. Check desktop/mobile layout locally. Record your observed results before describing Phase 6 as fully database-verified.

## Scope and limits

Graph construction has a 500,000 pair/movie observation guard and has not been benchmarked on a large real catalog. No full-team chemistry score, production simulation, budget-tier activation or draft action is implemented here. Source coverage is limited to imported eligible films; missing overlap is not evidence of incompatibility. Prices and gameplay assets remain unchanged.
