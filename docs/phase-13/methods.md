# Phase 13 — experiment methods and limits

All packaged experiment data are invented. No real player or TMDB sample was used in the balance study. Live API load tests and human sessions have not been run in this build environment.

## Balance experiment

The versioned [corpus generator](../../backend/app/validation/corpus.py) creates 84 fictional identities and 100 person-role profiles. Four identities each have all five roles; the remaining 80 are role specialists. Strength, popularity, experience and genre fit are deterministic synthetic attributes, **not** ratings calculated from real movie credits. Prices use the unchanged `fictional-fees-1.0` production formula and stay independent of the budget tier. Synthetic shared-film groups supply the twelve scored relationship edges.

Each of ten genres and three tiers has 20 seeds. Every seed is used by all three strategies, giving **1,800 completed drafts** and **600 paired comparisons against random for each alternative strategy**. This is one fixed catalog, not 1,800 independently sampled catalogs. The same seeds recur across genre/tier cells, so the aggregate 600 pairs are not independent population observations.

Each turn uses production `legal_candidates` and `choose_offer` with `pick:{slot}:{revision}`, starting at revision zero. Choose from the selectable cards in that three-card offer:

| Strategy | Choice rule |
|---|---|
| `random` | Highest deterministic SHA-256 rank of seed, slot and candidate identity |
| `genre_greedy` | Highest selected-genre fit; identity breaks ties |
| `star_heavy` | Highest popularity percentile; identity breaks ties |

These simple strategies do not reroll, recast, look ahead for chemistry, or inspect future offers. They do not optimize score or ROI globally. Selecting different people may change later eligibility and offers; the starting catalog and seeds are paired, not every later offer. Using the same release seed gives all strategies the same named noise draws within a cell.

Each final roster becomes a validated `phase7-v1` snapshot and runs through the unchanged `simulation-1.0` engine twice. The whole normalized result must match exactly. The CSV records the seed index, genre, tier, strategy, selected IDs, input/output hashes, spend, unused hiring budget, unrounded score, profit and ROI. The JSON records sample counts, mean, median, sample standard deviation, minimum/maximum and nearest-rank P10/P90 by cell, plus **within-seed differences** against random. P10/P90 describe observed synthetic variation; they are not confidence intervals. Dollar returns are fictional gameplay arithmetic.

The [audit command](../../backend/scripts/audit_balance.py) parses CSV numeric types, checks the canonical row hash, verifies exactly one row for every required cell/seed, and recomputes every published summary and paired denominator. `--replay` also recreates every draft with the current production engine. A content hash detects a mismatch; it is not a signature or proof of external provenance.

## Exact solver optimization

Profiling Phase 12 identified repeated enum role lookups inside the slot-mask loop. Phase 13 computes each person's eligible `(slot index, bit, fee)` entries once before iterating masks. It keeps the same candidate reduction, person order, slot order, snapshot of previous states, and lexicographic cost/witness comparison. There is no caching across catalogs or changed rule ID.

The [reference module](../../backend/app/validation/assignment_phase12.py) is the exact Phase 12 source, pinned by SHA-256 in a regression test. It is used only by tests and benchmarks; the API never imports it. Existing exhaustive small-pool tests remain an independent oracle. Eighty additional deterministic cases compare both the full witness and every candidate's legality, blocked reason, and completion cost over sparse/depleted multi-role pools, zero fees and ties. Ninety generated genre/tier/strategy cases also reverse the catalog iteration order and compare complete frozen inputs, traces and results. Three generated what-if controls verify all 64 paired samples have zero differences.

The benchmark uses four synthetic workloads, three warmups per function/case, seven alternating-order rounds, and twenty calls per timed round. It checks exact result equality before timing, stores all round samples and both source hashes, and reports median milliseconds per solve. A separate `cProfile` pass records the hot functions. Hardware/runtime are included. Timing varies with the OS and container contention; it is not a test threshold or an API response-time claim.

## HTTP load tool

The [API benchmark](../../backend/scripts/benchmark_api.py) accepts only a loopback HTTP origin with an explicit port. It runs GET requests, disables redirects/proxy inheritance/retries, caps concurrency at 16 and requests at 10,000, and validates success payloads with the application's schemas. Owner routes also require `Cache-Control: no-store`. Timeouts, non-200 responses, malformed JSON, schema failures and missing cache controls are errors, never fast successes.

The public profile equally cycles readiness, drafting catalog, the first 20 people and the first 20 eligible movies. Supplying your released practice draft adds draft, roster, saved result and analytics export. A hidden prompt or `CINEDRAFT_BENCHMARK_TOKEN` supplies the token; payloads, owner IDs and tokens are excluded from reports. The report retains only aggregate endpoint labels, counts and timings. The schema intentionally does not perform writes, release simulations, or stress tests of maximum capacity.

Warmups run before timing and must all succeed. Closed-loop worker threads reuse HTTP connections. Timing includes response body decoding and local schema validation; throughput uses the entire measured wall-clock interval. Per-route and total nearest-rank p50/p95 are provided for all requests and for successful requests separately. Concurrency is a maximum number of in-flight requests, not a fixed requests-per-second rate. A client on the same machine competes with the server for resources.

The tool uses `backend/.env` in a separate PostgreSQL READ ONLY transaction to record server version, migration head, active API catalog's matching dataset/pricing/graph IDs, catalog hash, person/movie/price counts, and total draft count. **Point those settings at the API's actual database.** Matching catalog IDs alone cannot establish that two independently seeded databases are the same server. Describe the API/DB hardware, worker count, container limits and reload setting in `--server-description`; the automatic machine metadata describes the load client.

No API measurements are included in this package. Run the workflows in the README on your local stack and retain both the request mix and environment when comparing runs. Avoid changing catalogs or creating drafts during a comparison. This read workload cannot establish transactional write capacity or internet-user latency.
