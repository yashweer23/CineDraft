# Phase 15 verification ledger

Observed during packaging on 7 November 2026. The source package is cumulative. Application version is 0.15.0; migration head is 0009_phase15. Python 3.12.14 and Node 24.22.1 were used locally.

| Check | Observed result | Scope |
|---|---|---|
| Backend suite | **604 passed; 113 skipped** | Includes 30 new policy, contract, HTTP authentication and WebSocket tests. Skips require real PostgreSQL. |
| Frontend tests | **60 passed** | Five new room tests cover random invites, stale snapshots, wrong-seat controls, credential-free socket URL, exact retry, live update/automatic-pick display and expired countdown. |
| Frontend TypeScript and Vite | **Passed** | Build includes the room UI and Vite WebSocket proxy configuration. |
| Original game | **4 passed** | Includes 540 generated legacy draft checks. |
| Existing browser journeys | **8 passed** | Four prior suites at 1280 and 390 pixels, with mocked HTTP. |
| New co-op browser journey | **Passed with two browsers** | Host at 1280px, partner at 390px; invitation, turn controls, lost acknowledgment, exact retry, live updates, timeout display, completion and reload recovery. HTTP and WebSocket messages are invented test responses. |
| Visual review | **Reviewed** | Desktop/mobile room cards, budget, roster and turn indicators; reflow checks passed. Internal QA screenshots are not release assets. |
| Source packager tests | **8 passed** | Reproducibility, no overwrite, path/security bounds and hash/manifest verification. |
| Backup wrapper tests | **3 passed** | Simulated subprocess tests, not a real backup/restore. |
| PostgreSQL room behavior | **Not run here** | Seven new cases: create/join/isolation/replay, full eight-pick freeze, solo bypass rejection, timeout/reconnect, cancel/conflicting receipts, and identical/different concurrent picks. |
| Real HTTP + WebSocket + PostgreSQL | **Not run here** | Run `scripts.room_smoke` on the local stack; included script is not evidence of a pass. |
| Restart and timeout with a running database | **Not observed here** | Follow README section 4. Unit policy tests establish the deadline boundary, not the whole worker/database behavior. |
| Docker/Windows, backup restore, hosted CI, public hosting | **Not run or performed here** | Prior outstanding live checks remain outstanding. No deployment, external repository push or message was sent. |

The refactored solo command body is reused within a caller-owned transaction. Existing backend unit regressions passed after the refactor; database constraints and lock behavior still need the PostgreSQL suite. The new migration was generated as frozen, reviewable PostgreSQL SQL from the two new models, but was not applied to a live database here.

The WebSocket unit tests run the actual ASGI route with a mocked persistence service. The browser test uses Playwright 1.51.1 / Chromium 134.0.6998.35. It proves interface behavior under the supplied messages, not network latency, database durability or multiplayer fairness under production load. The live smoke script refuses a non-synthetic catalog, creates one test film, and prints no player credentials.

## Before you call the local multiplayer stack verified

1. Back up your existing database, merge source, set the exact browser origins and rebuild images.
2. Apply `0009_phase15`; verify the migration head and run the full PostgreSQL integration suite.
3. Activate the fictional portfolio catalog and run the live two-player smoke command. Retain the actual JSON result.
4. Follow the two-window manual exercise. Let a 30-second turn expire, close/reopen a player, restart the API across an expiry, and check a host cancellation. Record what you actually observed.
5. Finish a real room, restore the host in the studio and release the resulting film. Compare the roster, fees and snapshot hash; the scoring engine is unchanged.
6. Keep cooperative observations separate from solo playtest data. Use your own measurements before claiming performance or usability results.
