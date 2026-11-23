# Hands-on Phase 10 exercise

Use your local synthetic catalog and a test database. Keep the API log terminal open and watch the Network panel for request paths/revisions. Do not copy bearer tokens or passwords into screenshots or commits.

1. Run the full PostgreSQL suite from the root README. Confirm migration `0006_phase10`, then register `studio_one` in one browser and `studio_two` in a separate private window. Registration allows five attempts per direct peer IP per hour.
2. Make a practice guest film, save its recovery token, then claim it into `studio_one`. Verify that its roster and locked fees remain identical, the guest token stops working, and `studio_two` cannot open it. A foreign draft read should return 404, not its contents.
3. Publish one challenge for today's local date. Inspect its pinned catalog and commitment in both browsers. Enter once in each. Choose the same actions initially; the offers should match. Different actions can create different histories.
4. Try entering a second time from `studio_one`. It must return `attempt_exists`. Use **Resume my attempt** to reopen the first film.
5. Pick all roles, finalize and release in both browsers before close. Verify that the studio confirms submission but does not display a release report, leaderboard rows or seed yet. A direct report read should return 423 for its owner and 404 for the other account.
6. After the actual deadline, refresh each draft and the leaderboard. Compare ranking order, saved report score and fictional profit. Inspect the public seed commitment. Never shorten the real deadline by editing database rows; use the integration tests for controlled boundary cases.
7. Change `studio_one`'s password. Its other account sessions should stop working, and a new login should still see its films. Guest claims remain owned and cannot be undone through the API.
8. Publish a future challenge with another catalog or tier. Check that it has its own leaderboard. Activating a different catalog must not change an existing challenge's offers or pins.

For an interruption exercise, stop the API after a request has been sent, restart it, then use **Retry same request** if the UI marks the outcome uncertain. A request that definitely returned but whose later read failed requires **Refresh draft**. Do not manufacture a new ID to force success.

Read `backend/app/accounts/service.py` to trace a claim and its lock order. Read `backend/app/challenges/service.py` and the submission SQL trigger together to trace a release into the ranking. The pure Phase 8 simulation engine remains unchanged.

Success means private ownership stays private, all retries preserve one attempt/submission, and the score shown after closing matches the owner's saved result. Record actual local outcomes in your notes; the mock browser checks do not establish these database facts.
