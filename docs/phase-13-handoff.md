# Next: Phase 13 — validate correctness, balance and performance

Start from the Phase 12 cumulative project, API 0.12.0 and migration `0008_phase12`. First run the included PostgreSQL 17 suite and a live owner export/replay exercise. Preserve all pinned catalogs, frozen results, SQL metric definitions, authorization boundaries, phase READMEs and local ports.

Follow the project's [Phase 13 roadmap](CineDraft_Development_Roadmap.md#phase-13--validate-correctness-balance-and-performance). Exercise generated drafts across genres, budget tiers, depleted pools and multi-role talent. Compare random, genre-focused and star-focused drafting strategies on the same seeds; report samples and variability. Verify accounting, deterministic release replay, paired comparisons and event deduplication.

Measure representative endpoints against a real database, documenting hardware, dataset size, request mix and concurrency. Record latency percentiles, throughput and error rate. Optimize one measured bottleneck and compare under identical conditions. Use browser tests on desktop and mobile; use real playtest feedback when available. Distinguish synthetic sessions from observed people throughout. Deliver reproduction commands, honest limits, a cumulative ZIP and the next hands-on README. No balance or performance certification is implied by Phase 12.
