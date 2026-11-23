# Phase 7 hands-on exercises

Start with the [root README](../../README.md). Use a synthetic practice catalog first; its small pool intentionally exposes shortages. Use an imported catalog with spare people for recast/reroll exercises.

## 1. Understand why the cheapest pick can be invalid

Run `python -m scripts.assignment_example` from `backend/`. Inspect the $500K exact assignment, then the disabled $100K writer. Change the budget to $1M in a local copy; the cheaper writer can then leave $900K for the other composer. Change it to $500K and verify the original $400K writer plus $100K composer remains exactly affordable. Remove the second writer and explain why the $500K completion disappears.

Read `app/drafting/assignment.py` after predicting each result. The key is exclusion by person identity across all professional profiles.

## 2. Verify the server controls money

Start a draft. Compare the candidate fee, pick's `locked_fee_usd`, talent spend and remaining budget after selection. In Swagger, submit an extra `fee_usd: 0` on the next pick request; expect 422. Read the draft again to verify no change. Try an unoffered person's UUID; expect rejection and unchanged revision.

A valid role profile elsewhere in the catalog does not make it a valid current offered choice. Do not edit source rows or sealed prices to test this.

## 3. Explore duplicate and competing actions

Use the exact PowerShell replay exercise in [api.md](api.md). A duplicate request returns the original response without spending again. Now change `person_id` while keeping its request ID; expect an idempotency conflict.

Restore the same token in two tabs and open the same draft. Pick in one tab. Pick from the stale offer in the other; expect 409. Refresh it and observe the committed pick. The integration suite additionally exercises truly concurrent requests from separate database connections.

## 4. Recast without losing the roster

Finish eight picks. Save the current roster, fees and revision from the inspector. Preview director, note the offer ID and alternatives, then cancel. Preview writer, cancel, and reopen director. Its alternatives and offer ID must match the first preview, while the current revision has advanced.

If an alternative is selectable, confirm it. Check `new_spend = old_spend - old_fee + replacement_fee`. Recasts used becomes one and the state becomes `review_locked`. No further preview is permitted. If the synthetic fixture has no alternatives, cancel; no fee or allowance is consumed.

## 5. Freeze and resume

Finalize the roster and record its snapshot hash. Restart your services without removing the database volume. Restore the same token and open the saved draft. The roster and hash should match; there is no release simulation button yet.

Activate a different compatible catalog and open this old draft again. Its `versions.catalog_id`, pricing and graph pins must remain the originals. New drafts use the new activation.

## 6. Read the transaction tests

Start with `backend/tests/test_draft_integration.py`: ownership, receipt failures, rollback, short offers, cached recasts and snapshot immutability. Then inspect `test_draft_concurrency.py`: one new action wins at a shared revision, or duplicate requests return the same receipt. Run these against real PostgreSQL with the verification command before treating them as passed.

The pure matching tests independently enumerate small assignments rather than relying on the implementation's DP recurrence. Try adding a person with both writer and composer credits to one randomized case, then check the exhaustive result.
