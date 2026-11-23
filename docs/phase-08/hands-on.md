# Phase 8 hands-on exercises

Use the root README to upgrade to `0005_phase8`. Keep your private token and database volume. These exercises are for fictional game arithmetic and engineering, not real film forecasting.

## 1. Reconcile a known example by hand

Use `G=60`, `T=80`, `H=60`, cast appeal 50, talent spend $3.25M and envelope $6.5M. Efficiency is `(60+80)/2 × (1−0.30×0.5) = 59.5`. Contributions are 18, 24, 15 and 8.925. The unrounded studio score is 65.925, rounded to **66**.

With all release noise set to zero in an arithmetic test, critics are 70, audience 64 and gross multiplier 2.752. For production $6.75M: gross $18.576M, marketing $1.35M, receipts $9.288M, total cost $8.1M and profit $1.188M. These zero-noise values differ from the bundled seeded example, which deliberately includes its saved random draws.

Read `backend/tests/test_simulation_engine.py` to compare the manual arithmetic with assertions. The HTTP API cannot accept a custom noise override.

## 2. Repeat a synthetic release

From the backend virtual environment, run `python -m scripts.simulation_example` twice. Compare output hashes and the three random draw records. They match because the seed, frozen inputs, algorithm, precision and formula versions match.

In a local copy of the example, change only the seed. The studio score stays the same; simulated reviews and financial output may change. Then change selected talent or genre fit together in the synthetic card and its matching role profile. Explain why that can change the studio score. In real persisted games, do not edit sealed snapshots to perform this exercise.

## 3. Observe chemistry saturation

Call the synthetic snapshot helper with zero, three and six shared films per designated edge in a test or scratch script. Chemistry is neutral 60 at zero and reaches 100 when every edge has three films. Six shared films retain all evidence but cannot increase the bonus beyond three. Confirm twelve relationships are used, not all possible roster pairs.

In the studio, open a released film's chemistry section, inspect a pair and page through all shared evidence. Verify that job labels match the displayed people even when their UUID order differs from slot order.

## 4. Prove that retries do not reroll

Use the PowerShell replay in [api.md](api.md). Submit the same command ID/body twice, then compare attempt ID, result hash and current revision. They should not change. In a second tab, refresh and observe the same saved film.

For engine-failure recovery, read the integration test that deliberately makes the calculator raise an exception. It stores a generic failed attempt, then restores the engine and retries with a new command. The resulting JSON must match a direct calculation from the original snapshot. This test does not alter your normal game data.

## 5. Verify persisted replay

Release an owned finalized draft. Copy its UUID and run `docker compose run --rm api python -m scripts.verify_release --draft UUID` from the project root. Expect `matched: true`, zero writes and zero upstream requests. Restart services while preserving the database volume and repeat.

Activate a newer drafting catalog and verify the old film again. Its replay must still use its frozen inputs and match. A newly activated price or graph version must not rewrite a finished film.

## 6. Separate a high gross from profit

In the results screen, calculate `studio receipts − production − marketing` and compare it with saved profit. Confirm the weekly values sum to gross. Explain why a film with a positive gross can still lose money after the studio share and marketing.

Now compare studio score against profit. A different seed can change profit without changing studio score. Compare strategic scores only within compatible tiers and version/mode boundaries; this phase does not add a leaderboard or balance certification.

## 7. Run the real database gates

Run the Docker PostgreSQL verification command from the root README. Inspect the tests for duplicate/concurrent release, result-write failure, attempt-write failure and receipt-write failure. In every persistence failure, the draft must return to its prior state with no partial result or attempt. These tests were collected but not executed in the packaging environment.
