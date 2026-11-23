# Phase 8 scoring and release design

## Frozen inputs are the authority

The pure engine accepts finalized `phase7-v1` snapshots and their canonical SHA-256 hash. It verifies the supported rules/scoring versions, exact configuration equality and graph manifest hash. Selected feature profiles must match the eight cards and selected professional roles. It does not read current catalog prices, current popularity, a new graph or live TMDB data.

The Phase 7 `scoring:baseline-1.0`, `rules:classic-1.0`, offer PRNG and `simulation-1.0` pins remain unchanged. The simulation now supplies the concrete random-number mapping and arithmetic manifest for the previously reserved simulation version. Older `phase3-v1` fixtures/results remain readable through their existing helpers and are not treated as real release-engine inputs.

There are two separate random specifications: the frozen draft's `sha256-order-1.0` generates offers; the result's `sha256-uniform53-1.0` generates release noise. They do not share mutable state.

## Scoring

All model arithmetic uses Python Decimal at precision **64**, with `ROUND_HALF_UP`, in local contexts. Decimal source strings/numbers are read without a binary floating-point arithmetic step. Public simulated review display values have two decimals; full-precision values and components are retained as decimal strings. Frontend formatting of these strings also uses half-up rounding.

Slot weights follow the frozen order: director 1.5; lead 1.3; co-lead 1.1; supporting 1/2 each 0.7; writer 1.4; cinematographer 1.1; composer 0.9. `G` and `T` are the weighted genre/talent means. `P` is mean popularity of the four actors, using neutral 50 for missing popularity; an observed zero stays zero.

The engine requires exactly the twelve designated ordered collaboration relationships. Canonical endpoints must match the selected people and professional roles. Distinct movie evidence, counts and bonuses must reconcile. Each edge contributes `min(12, 4 × shared films)`; zero evidence is absence, not incompatibility.

```text
H = 60 + 40 × sum(edge bonuses) / 144
q = (G + T) / 2
u = talent spend / talent envelope
E = clamp(q × (1 − 0.30 × u), 0, 100)
studio score = round_half_up(0.30G + 0.30T + 0.25H + 0.15E)
```

The studio score is deterministic and independent of release noise. It contains no direct popularity, budget-size or revenue bonus. The report retains each component and contribution, all eight role rows, top two weighted genre contributors, source coverage warnings and twelve chemistry evidence links. Popularity can affect simulated audience and financial outputs without directly affecting studio score.

## Reproducible random streams

For each stream `critics`, `audience`, `revenue`, at draw index zero:

1. Canonically encode JSON `["sha256-uniform53-1.0", frozen_seed, stream, 0]` using sorted keys where relevant, compact separators and UTF-8.
2. Compute SHA-256; take the first 64 bits and shift right by 11 to obtain an unsigned 53-bit integer `n`.
3. Map to `u = n / 2^53` using Decimal. This gives one of 2^53 equally spaced values in `[0,1)`.
4. Compute `low + (high − low) × u`. Review bounds are `[-5,5)`; revenue bounds are `[-0.6,0.6)`.

No clock or process-global random state is used. A future extra draw in one stream does not perturb another stream. The manifest records the mapping, precision, bounds, draw index, one iteration and rounding. Each draw records its digest, integer, exact unit value and noise. The result exposes the frozen seed after release for inspection.

Simulation identity is UUIDv5 under the URL namespace using `cinedraft:simulation-1.0:<input_hash>`. All failed attempts and retries for those inputs target that same identity. Request IDs, attempt timestamps and retry counts do not affect output JSON.

## Fictional release and finances

```text
critics = clamp(0.50T + 0.35G + 0.15H + review noise, 0, 100)
audience = clamp(0.30T + 0.30G + 0.20H + 0.20P + review noise, 0, 100)
k = clamp(0.50 + 0.018audience + 0.010critics + 0.008P + revenue noise, 0.2, 5.0)
production = production reserve + locked talent spend
gross = round_half_up(production × k)
marketing = round_half_up(0.20 × production)
receipts = round_half_up(0.50 × gross)
total cost = production + marketing
profit = receipts − total cost
return % = 100 × profit / total cost
```

Unrounded reviews feed subsequent formulas. Each named financial output is rounded to integer USD. Marketing is additional modeled release spending; unused talent authorization is not committed production cost. The model excludes streaming, merchandising, financing, tax and contractual participation. A high theatrical gross can still yield a loss after the studio split and marketing.

Retention is `clamp(0.40 + 0.004 × audience, 0.40, 0.80)`. Normalize weights `[1,r,r²,r³]`; floor weeks 1–3 to dollars, then assign the residual to week four. The totals reconcile exactly. This is a stylized game outcome, not a calibrated revenue forecast.

## One atomic release command

`POST release` requires `production_finalized`; a new `POST retry-simulation` requires `simulation_failed`. Both authenticate the owner, lock the draft and check an existing command receipt before validating the expected revision. Same command ID/body returns its saved response. Reusing the ID with different fields gives 409. Another owner's token cannot read or replay it.

Within one transaction, the service validates the frozen snapshot, temporarily marks the draft `simulation_running`, calculates the result, saves it, records the immutable attempt, advances revision once and writes the command receipt. Only then does the service return. CPU computation is synchronous, with no upstream requests or queue. Readers may wait for the draft lock rather than observe an intermediate running state.

A successful attempt stores a `phase8-v1` result and `results_available`. The existing result primary key permits only one result per draft; results remain append-only. No later action can change the roster or reroll the result.

An unexpected computation exception stores a generic `engine_error`, a failed attempt and `simulation_failed`, without a result. The response is HTTP 200 because the command itself was recorded; the attempt explicitly says `failed`. Logs include only draft ID, command ID and exception type, not arbitrary exception text or secrets. A new retry after fixing the issue uses the same frozen inputs and seed.

Unsupported/inconsistent inputs return 422 without a committed attempt or revision. SQL failures propagate as sanitized 503 and roll back everything. A process crash also rolls back its open transaction, so there is no durable orphaned running state. A lost commit acknowledgment remains uncertain: repeat the exact command ID/body; do not create a new command to guess whether it committed.

Old receipts stay old after later actions. For example, replaying a failed release receipt after a successful retry still describes the failed attempt. GET draft/status/result reads current state.

## Persistence and compatibility

Migration `0005_phase8` adds `simulation_attempts` (32 tables total), unique draft/attempt-number and command/request keys, append-only enforcement, and outcome consistency guards. A new result must agree with its running draft and frozen input identity. A successful attempt must have its matching result; a failed attempt cannot have a result. The attempt sequence follows the locked draft.

Earlier migrations are preserved. The downgrade refuses while Phase 8 attempts or results exist. Existing Phase 7 draft snapshots and catalogs are not rewritten. The historical fixture result bypasses only the Phase 8-specific result guard because it has a separate old schema; its existing immutability protections remain.

`contracts/result.phase8.schema.json` documents result JSON. The result hash covers its canonical JSON, including explanatory data, versions, seed, random draws and arithmetic manifest. Attempt and receipt timestamps are outside that hash. `scripts.verify_release` reads only frozen inputs and the saved result, recomputes, and compares both full JSON and hashes without updating rows.
