# Phase 10 API additions

Base URL: `http://localhost:8001`. Current OpenAPI: `/api/openapi.json`; interactive docs: `/api/docs`. Private paths require `Authorization: Bearer <account-or-guest-token>` as applicable. Tokens are never query parameters. Account/challenge responses use `Cache-Control: no-store`.

| Method and path under `/api/v1` | Authorization | Body / result |
|---|---|---|
| POST `/accounts/register` | Public, throttled | `{username,password}` → 201, bearer token, expiry and account |
| POST `/accounts/login` | Public, throttled | Same credentials → 200, new bearer session |
| GET `/accounts/me` | Account | Account ID and public username |
| POST `/accounts/logout` | Account | Revokes this bearer session |
| POST `/accounts/claim-guest` | Account + guest proof | `{guest_token}` → film count; permanent whole-session claim |
| POST `/accounts/password` | Account | `{current_password,new_password}` → all sessions revoked |
| GET `/challenges` | Public | Paginated public definitions, newest opening first |
| GET `/challenges/{id}` | Public | One pinned public definition; no raw seed |
| POST `/challenges/{id}/attempts` | Account | `{request_id}` → 201, standard LiveDraft; idempotent exact replay |
| GET `/challenges/{id}/mine` | Account | `{draft_id}` or `{draft_id:null}` |
| GET `/challenges/{id}/leaderboard` | Public | Challenge, ranked items, next offset, explanation; empty before close |
| GET `/challenges/{id}/audit` | Public after close | Seed, commitment and algorithm; 423 beforehand |
| GET `/drafts/{uuid}/challenge` | Owning account/guest | `{challenge:null,submitted:false}` for practice, or challenge context |

Lists use `limit` 1–50 and `offset` 0–100000. Challenge entry accepts no extra fields: seed, score, genre, tier and catalog overrides are rejected with 422. Publication is CLI-only. The existing draft/create/pick/recast/finalize/release endpoints now accept account sessions in addition to eligible guest tokens. Existing `LiveDraft` shapes are unchanged.

A qualifying release automatically inserts the submission. `/drafts/{uuid}/result` returns 423 for a still-open challenge even after successful release; no separate report route bypasses that rule. Status reads can say a result exists without exposing it.

Common errors: 401 invalid/expired session or wrong credentials, 404 foreign/missing draft, 409 conflicting ID / already used attempt / closed challenge, 422 malformed or forged input, 423 report/seed embargo, 429 authentication throttle, 503 database failure. Validation and database responses do not echo credentials. See [recovery](recovery.md) before retrying an uncertain write.

Generate current OpenAPI and Phase 10 schemas from `backend/` with `python -m scripts.export_phase10_contracts`. The exporter does not connect to the database or overwrite historical snapshot/result schemas.
