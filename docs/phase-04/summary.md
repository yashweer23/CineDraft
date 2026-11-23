# Phase 4 implementation summary

The backend now consumes TMDB explicitly from the terminal and exposes published raw catalog data. This is a cumulative local VS Code project, with no hosted deployment.

| Area | Implementation |
|---|---|
| Source client | Header authentication, restricted read paths, timeouts, bounded retries, rate-limit handling, image configuration |
| Validation | Typed source payloads, positive IDs, finite values, missing-value handling, exact role mapping |
| Scope | Released English feature policy, documentary/TV exclusions, conservative cast filters, film review queue |
| Persistence | Two new tables, frozen checkpoints, one active CLI importer, atomic sealed dataset publication |
| Provenance | Per-resource hashes/timestamps, configuration manifest, original credit labels and manual review decisions |
| Catalog | Five live read-only routes plus existing health endpoints, pagination and exact role-specific films |
| Developer workflow | CLI smoke/start/resume/status/review/publish, configurable host API port, current OpenAPI export, exercises |
| Credits | TMDB notice and external logo link in the studio |

The schema now has 23 domain/import tables. `0002_phase4.py` adds import state and guards; historical `0001_phase3.py` remains byte-identical. The original four gameplay assets are unchanged. No `.env`, live credentials, downloaded dataset, dependency folders or generated build output are packaged.

An import can publish eligible films while preserving excluded/review entries for audit. It cannot prove complete careers, a fair draft pool, price feasibility or playable game balance. Dataset playability remains false. Film lists are chronological raw credits, not ranked notable works. Phase 5 adds talent features, fictional fees and ranked works; Phase 6 collaboration; Phase 7 authoritative draft actions; Phase 8 simulation; Phase 9 final game UI.

See [verification](verification.md) for observed results and unexecuted local gates. The implementation is delivered even though PostgreSQL/Docker and authenticated TMDB execution are unavailable in this environment; those checks must pass on your setup before treating ingestion as verified end to end.
