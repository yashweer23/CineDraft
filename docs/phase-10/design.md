# Phase 10 design

## Authentication and ownership

Account usernames are public normalized ASCII handles. Passwords retain exact whitespace and Unicode. `scrypt-1` uses N=32768, r=8, p=3, a random 16-byte salt and a 32-byte derived key; comparison uses constant-time digest comparison. Verification accepts only supported parameters, preventing a corrupt stored hash from requesting unbounded work. Missing users perform the same derivation against a dummy hash. A small obvious-password blocklist is included; it is not a full breached-password service.

An `acct_` prefix separates account sessions from guest capabilities. Account tokens contain 32 random bytes encoded as 43 URL-safe characters after that prefix, expire after eight hours, and are stored only as SHA-256 digests. They are sent in the Authorization header. The UI holds tokens and secrets in memory, clears password/proof fields after submission and uses no browser storage. Sign-out revokes one account session; password change/reset revokes all. Login creates another session; refresh does not renew one.

No ambient authentication cookie is used. Cross-origin credentials remain disabled and CORS accepts configured local origins. This avoids cookie-based ambient authorization, but does not protect a token from malicious same-origin script. Loopback HTTP is the supplied environment. An Internet deployment needs its own TLS, origin/proxy, request-size, abuse and lifecycle review.

Authentication attempts are reserved in their own committed transaction before password verification: registration 5/hour per direct peer IP; login 30/15 minutes per direct peer IP and 10/15 minutes per normalized username. Limits count successful attempts too. Independent hashed buckets contain bounded timestamp arrays; login failure cannot roll them back. Forwarded headers are not trusted. With a proxy, users may share a peer bucket. Stale bucket rows are retained; cleanup and distributed perimeter controls are future work.

Accounts have a stable internal guest owner identity whose raw credential is never issued and is already revoked. `account_ownership` links this identity and any claimed guest identities to an account. All draft/roster/release reads and writes use that ownership scope. A claim locks and validates the old guest session, adds an immutable mapping and revokes guest access atomically. It claims all films, preserves immutable historical owner hashes and does not rewrite snapshots. A repeat by the same account is safe even after the claim revokes the guest token.

Account authorization reads the token's account identity, then locks the account before the session. Normal operations take shared account locks; account creation of films, claims, password changes and logout serialize with exclusive account locks. Draft writes retain their row lock and receipt-first processing. Guest operations still lock their guest identity; claims wait for earlier guest work to finish. Ownership, not a request ID or draft UUID, authorizes every replay.

## Official challenge policy

`daily-1.0` is a separate competition policy. It does not change `rules:classic-1.0`, `scoring:baseline-1.0`, offer PRNG `sha256-order-1.0`, release PRNG `sha256-uniform53-1.0`, `simulation-1.0`, or the Phase 7/8 input/result schemas.

A publication stores the full version bundle, catalog hashes, simulation manifest hash, genre/tier, local date, IANA timezone and concrete UTC boundaries. Local midnights are converted separately, so DST days can contain 23 or 25 hours. Existing challenge rows are immutable; later timezone data or active catalog changes do not rewrite them.

The server creates a 256-bit hex seed and publishes SHA-256 of its ASCII representation as a commitment. All participants share that secret seed. Matching action histories produce matching offers; player choices still affect future availability. The only public attempt input is a request UUID. An account lock and database uniqueness enforce one attempt per account/challenge. An identical creation request replays its original receipt; a different ID cannot allocate another attempt. Failed or abandoned attempts still consume the allowance.

Fresh picks, rerolls, recasts, finalization and release require the challenge to be open. The application checks database `clock_timestamp()`; insertion guards independently check attempt, submission and action-record times. The submission trigger assigns the database time rather than trusting supplied timestamps. A transaction that fails any persistence/deadline guard rolls back its draft state, result, attempt, submission and receipt. A deadline reached after a statement can cause rejection at the later guard. Qualification is enforced at those database write checks, not by a client clock or response-arrival time.

A successful release writes its official submission inside the existing transaction, taking score, profit and output hash from the saved server result. Foreign keys bind submission to the exact attempt/account/challenge and result. The SQL trigger checks those values. There is no public submission route, arbitrary score field, practice promotion or leaderboard reroll.

Before closing, public rankings are empty and audit/result reads return 423. Result access checks ownership before embargo. Draft/status/roster receipts contain no seed. After closing, public ranking order is score DESC, profit DESC, submission time ASC, draft UUID ASC. Ranking responses reveal username, score, profit, timestamp and output hash; full reports remain owner-only. This is a trusted local competition model, not a defense against multiple accounts, collusion or a database operator.

## Compatibility and recovery

Migration 0006 adds seven tables, replacing only the runtime owner guard's authorization branch. Earlier migrations are byte-for-byte preserved. The 39-table metadata and new downgrade refusal are covered by PostgreSQL tests that still need local execution. Historical Phase 3 fixtures and Phase 7/8 films remain intact.

The guided studio loads draft, matching-revision roster and challenge context after mutations. It fails closed if context cannot be read. Exact pending requests survive in memory and can be exported without a token. Account sessions can expire while a request is uncertain; a fresh login to the same account can replay the same draft/challenge request. See [recovery](recovery.md).

## Primary references

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html): scrypt parameters and salted password hashing.
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html): password length, generic login responses and throttling.
- [Python tzdata documentation](https://tzdata.python.org/): IANA fallback data, including Windows usage. The project pins 2025.2; challenge rows record concrete UTC boundaries.

These references informed the choices; they are not a security certification of this application.
