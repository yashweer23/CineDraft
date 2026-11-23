# Phase 11 hands-on exercises

## First: arithmetic without services

Run `python -m scripts.whatif_example --control` from `backend/` with the configured Python environment. Inspect every metric: original and alternative distributions match; paired P10, median and P90 are zero; equal count is 64. Studio score stays 66.

Run `python -m scripts.whatif_example`. The invented alternative director costs $450,000 versus $406,250. Talent spend becomes $3,293,750; the untouched reserve is $3,500,000; production is $6,793,750 and additional marketing is $1,358,750. Studio score becomes 68. The sample hash is identical to the control's sample hash. Running again produces the same output hash.

Open `app/whatif/example.py`. Adjust talent strength or drama fit in both the card and role attributes, rerun, and explain which score components change. A director's popularity does not change cast appeal; try changing a cast role only after correctly rebuilding that role's identities and graph endpoints. The validators deliberately reject inconsistent mock teams.

The JSON fixture at `frontend/src/testdata/whatif-example.phase11.json` was generated from this engine. Its receipt UUIDs/timestamps are invented UI test data, not records in your database.

## Then: a real saved film

Use a film drafted and released through your actual API, with a catalog containing at least two candidates for the role. The eight-person starter fixture supplies only one director; it remains useful for the control. You do not need to modify or migrate that fixture to run the standalone arithmetic exercise.

1. Record the film's revision, frozen input hash and official output hash from the studio's details. Keep its official studio score/profit for comparison.
2. Run the original-person control. Verify all paired changes are zero.
3. Select an affordable alternative. Check the old fee is refunded and the replacement price matches its card. Inspect costs and component changes, then shared-film titles and credited jobs.
4. Run the same comparison again. Its analysis UUID, created time and output hash should be identical.
5. Load history, reopen the report and run `python -m scripts.verify_whatif --analysis <UUID>`. Expect `matched: true` and zero writes.
6. Refresh the official release and compare the values recorded in step 1. Revision, inputs, official score and output hash should be unchanged.
7. Sign in to a second account. The first account's draft/report must not become accessible just by knowing the UUID. Do not copy the first owner's token into the second session.
8. If using a guest film, claim it through the account UI. Its saved comparisons should remain readable from the account; the old guest token should be rejected.

## Challenge and recovery exercises

Complete a challenge before its deadline. The lab button should remain hidden; authenticated direct candidates/history/report/create calls should return 423. After the deadline, refresh the film and repeat the control. The official leaderboard score must remain unchanged.

To test an uncertain response locally, use the included mock browser test (`npm run test:browser:phase11`). It deliberately loses a comparison acknowledgment, checks sign-out/navigation are blocked, retries the exact request body, then reopens the saved report without another POST. This scripted mock is separate from the live database tests.

Do not edit immutable source rows, disable SQL guards or change the database clock to perform a live exercise. The automated PostgreSQL tests use disposable isolated schemas and explicit test clocks where appropriate.
