# Phase 9 hands-on exercises

1. **Trace one pick.** Use the browser Network panel on your local machine. Select a candidate but cancel the confirmation. No pick POST should occur. Confirm a different selection; inspect the request keys, then the follow-up GET draft and GET roster. Do not share bearer headers or token screenshots.
2. **Follow a saved name.** Inspect `service.roster` and the `OfferCandidate.card_snapshot` lookup. Restore a session after refresh. Confirm the name and films come from the selected saved offer, not a current catalog search.
3. **Inspect a blocked choice.** Find a disabled candidate. Read its server explanation. Compare the UI's projected balance with the committed balance after a legal pick. The browser's preview never overrides the API's decision.
4. **Test a recast cancellation.** Complete eight roles, note all money values, preview a replacement and cancel. Reopen the same slot and compare offer IDs in developer state. Names, fees and budget should stay unchanged until confirmation.
5. **Follow an uncertain response.** Run the default browser test. Its first pick commits to the test fixture and returns a simulated 503. Exact replay returns the original receipt, followed by current-state reads. Inspect the assertions comparing request bodies. This demonstrates UI logic, not a real database outage.
6. **Compare read failures.** In `Studio.test.tsx`, find the case where a committed POST is followed by a failed roster GET. The next action is Refresh draft, with no extra pick POST.
7. **Try the keyboard.** Tab through a candidate, open its dossier with Enter, then press Escape. Focus should return to that dossier control. Open a selection confirmation and cancel; confirm that no API mutation happened.
8. **Read a result.** Compare gross, receipts, costs and profit. Expand chemistry evidence and inspect exact jobs. Use `scripts.verify_release` from the Phase 8 guide to independently replay a real saved result.
9. **Change presentation only.** In a copy, adjust spacing or typography in `frontend/src/styles.css`; run component tests, build and browser checks. Keep rules, source schemas and simulation manifests unchanged.

Use the real PostgreSQL suite and live browser mode locally to verify the database-backed path. Do not present the mocked browser run as a full-stack test.
