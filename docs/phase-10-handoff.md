# Phase 10 — accounts, daily challenges and leaderboards

Continue with a cumulative VS Code ZIP and standalone README. No deployment is requested. Start from Phase 9: API 0.9.0, migration `0005_phase8`, guided React studio plus the earlier developer tools. Preserve the user's ports 5433/8001/5174, private `.env` files and original prototype.

## Before extending ownership

Read the Phase 1 rules/UX documents, Phase 7 capabilities and immutable drafting design, Phase 8 scoring/replay design, and Phase 9 current-state/recovery behavior. Run the real PostgreSQL suite and live browser journey locally: Phase 9 observed 262 backend unit passes, 39 frontend passes, 4 legacy passes and two mocked browser journeys, but all 66 PostgreSQL cases and live browser mode remained unrun.

## Next implementation scope

1. Design an account/session model alongside the existing guest route. Choose and document local-development authentication, password handling, session expiry, CSRF/CORS boundaries and credential storage before implementing UI. Do not disguise guest capability tokens as secure long-lived accounts.
2. Define an explicit, authorized way to claim eligible guest films into an account without weakening existing owner checks or changing historical records. Token possession and account ownership must be checked server-side; expired/lost capabilities must not silently become claimable by draft UUID.
3. Add migrations and tests for account ownership, sessions and history. Preserve historical migrations and all existing guest films. Recovery, renewal and revocation need clear product rules; no automatic email sending or external service setup is authorized by this handoff.
4. Model each daily challenge as an immutable catalog/rules/scoring/simulation bundle, schedule/timezone, budget/genre scope, attempt policy and tie-breakers. Define whether first or best attempts count before writing a leaderboard.
5. Give official challenge attempts reproducible server-owned offers and score inputs. Do not expose unreleased seeds in public challenge responses. Do not let users select a seed, claim a client-computed result, or compare incompatible budget/rules groups on one undifferentiated ranking.
6. Keep official submissions separate from practice films and future hypothetical analyses. Enforce deadlines and attempt limits transactionally, including retries and simultaneous requests.
7. Add the account, challenge and ranking screens without losing the guided brief/draft/review/release flow or its named roster. Preserve exact-request replay, current-state refresh, clear privacy boundaries and memory-only guest handling until an explicit replacement design exists.
8. Test two independent accounts: private drafts stay private, retries do not create extra attempts/submissions, and arbitrary client scores are rejected. Run real PostgreSQL and browser-to-API/database checks where possible; label any unrun gate accurately.
9. Regenerate current contracts, write migration/rollback and hands-on instructions, package the ZIP/README, and leave a Phase 11 handoff for the controlled “What if?” lab.

Never silently change `phase7-v1` snapshots, `phase8-v1` results, `scoring:baseline-1.0`, `simulation-1.0`, existing random stream behavior or historical financial arithmetic. New competitive rules need new explicit version identities and compatibility rules.
