# Phase 3 verification

Recorded 21 October 2026. This report distinguishes completed checks from runnable checks supplied for the user's machine.

## Passed in the delivery environment

| Check | Result |
|---|---|
| Backend unit/contract suite | 26 passed; 13 real-PostgreSQL cases skipped explicitly because no server is available |
| Existing health/error/CORS behavior | Preserved by the original 13 backend tests |
| New contract behavior | Strict integer USD; reconciled budgets/results; server-owned request fields rejected; five-film limits/deduplication; complete unique frozen rosters and matching fees/versions; hash stability; future routes absent |
| Contract export | 15 distinct proposed OpenAPI paths; saved export matches generator; draft operations declare future bearer authentication |
| Migration rendering | Offline upgrade/downgrade SQL succeeds; all 21 table and three index definitions match model-generated SQL after normalizing constraint order |
| SQL syntax | Upgrade/downgrade statements and all eight PL/pgSQL functions parse with a PostgreSQL parser; this is syntax validation, not execution |
| Original game | Four existing tests pass, including 540 complete seeded drafts; four original assets remain byte-identical |
| React | Four existing tests pass; strict TypeScript/Vite production build succeeds |
| Packaging | Archive contents, source preservation, internal documentation links and excluded secrets/dependencies checked |

Backend dependencies remain the Phase 2 lockfile. No new application dependency is needed. A scratch-only SQL parser was used for syntax review and is not an application requirement.

## Real PostgreSQL checks included, not executed here

The 13 integration cases cover the existing connection check plus:

- Upgrade from empty schema, repeat upgrade, metadata comparison, downgrade and re-upgrade in an isolated schema.
- Synthetic seed and no-op repeat, multi-role credits, snapshot/result round-trip and request replay/body-conflict handling.
- Rejection of immutable-row edits, unsealing, late member inserts, snapshot/result modification, overspending, seed changes and duplicate action identity.
- Duplicate person across two roles, cross-draft offer misuse, and independently rejected candidate/pick price substitutions.

Run from the root:

```powershell
docker compose --profile verification run --rm --build api-tests
```

Or from `backend/` with its activated virtual environment:

```sh
python -m scripts.run_integration
```

The runner enables integration using your backend settings. Tests create uniquely named schemas in an outer transaction and roll them back afterward; they do not reset the application schema. PostgreSQL connectivity or constraint failures are test failures, not skipped successes.

## Remaining gates

1. Execute the real PostgreSQL suite and migrations on PostgreSQL 17. Syntax parsing does not prove trigger behavior, FK enforcement or SQLAlchemy round-trips.
2. Build/start Docker Compose on a Docker-capable machine. This environment has no Docker engine. Compose structure and file references are checked, but container execution is not claimed.
3. Perform Windows command verification and the local acceptance checklist in [hands-on.md](hands-on.md). Work here ran on Linux with Node 24.19.0 and Python 3.12.14.
4. Recheck the studio in a real browser. No new gameplay layout was introduced; only phase/status copy changed. DOM/build checks do not replace visual verification.
5. Execute GitHub Actions after uploading the project to your own repository. The workflow is provided, but no remote workflow was run or repository published.

Phase 3 is delivered as implementation plus executable verification gates. It is not claimed to be a verified running PostgreSQL/Docker deployment.
