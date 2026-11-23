# Learn by inspecting Phase 3

Start with the migration and synthetic fixture commands in [setup.md](setup.md). No TMDB key is needed.

## 1. Follow one person through the model

Open `backend/app/fixtures.py` beside `backend/app/models.py` in VS Code. Find the director's fixture identity. It has two credits/profiles: director and writer. It still appears once in `people` and once in the draft roster.

Run the fixture inspection command and find `cards`, `draft.picks`, `draft.versions`, `seed` and `budget`. Why does the person identity differ from the role profile key? Because changing a person's profession must not allow hiring the same person twice.

The fixture spends $850,000 of the $6,500,000 talent envelope. The reserve is $3,500,000, so production commitment is $4,350,000. The synthetic result uses $870,000 marketing, $10,000,000 gross, $5,000,000 studio receipts and a $220,000 loss. These are handwritten values to test storage and accounting; no scoring/simulation formula ran.

## 2. Query the database

With the default local user/database names, run from the project root:

```powershell
docker compose exec db psql -U cinedraft -d cinedraft
```

If you changed the names in `.env`, use your own user/database names. Inside psql, these are read-only queries:

```sql
SELECT version_num FROM alembic_version;

SELECT p.source_key, s.name, c.role, c.job
FROM people p
JOIN person_snapshots s ON s.person_id = p.id
JOIN credits c ON c.person_id = p.id AND c.dataset_id = s.dataset_id
WHERE p.source_key = 'fixture:person-director';

SELECT d.id, d.status, d.total_budget_usd, d.reserve_usd,
       d.talent_budget_usd, d.talent_spend_usd,
       d.talent_budget_usd - d.talent_spend_usd AS remaining_usd
FROM drafts d
WHERE d.dataset_id = 'fixture:dataset-v1';

SELECT draft_id, count(*) AS slots, count(DISTINCT person_id) AS people,
       sum(locked_fee_usd) AS talent_spend_usd
FROM picks GROUP BY draft_id;

SELECT command, revision_before, revision_after, response_status
FROM action_records ORDER BY revision_after;

SELECT input_hash, jsonb_pretty(inputs->'draft'->'versions')
FROM draft_snapshots;

SELECT outputs->>'profit_usd' AS fictional_profit_usd,
       outputs->>'synthetic' AS synthetic
FROM results;
```

Exit psql using `\q`. The synthetic action rows illustrate persistence and replay lookup. They are not proof that the complete state machine or simulation job lifecycle ran.

## 3. Read the integrity rules

Find these model constraints and matching migration statements:

- `UniqueConstraint("draft_id", "person_id")`: a multi-role person cannot fill two slots.
- The pick's composite offer foreign key: another draft's offer cannot be reused.
- The candidate/fee foreign key: a stored pick cannot silently substitute a different fee.
- `cd_member_guard`: no new members after a version or offer is sealed.
- `cd_pick_guard`: the finalized roster cannot be edited.

Run the real integration suite to exercise rejection cases in isolated temporary schemas:

```powershell
docker compose --profile verification run --rm --build api-tests
```

The tests attempt invalid writes and verify rejection. You do not need to make intentional invalid edits in your own application data.

## 4. Inspect a contract

Open `backend/app/contracts.py`. `PickRequest` accepts a request UUID, expected revision, offer UUID and person UUID. It deliberately has no price field. In `contracts/openapi.proposed.json`, find `/api/v1/drafts/{draft_id}/picks`, its planned marker, request schema, error response and bearer requirement.

Try the running `/api/docs`: it still has only health endpoints. A JSON contract is a shared definition; Phase 7 must implement the actual transaction.

## 5. Make one safe local change

Add a descriptive field to a copy of the fixture's `coverage` object and inspect the Python code. Do not modify an already sealed dataset in place. If you want to load a different fixture, give the entire fixture dataset, related version IDs and deterministic fixture identities a new namespace/version before loading it. Existing frozen snapshots must continue to reload unchanged.

For actual schema changes later: edit the models, generate a new Alembic revision, review its SQL, and test upgrades on an isolated database/schema. Never edit a migration that you have already applied to a shared database. Keep `0001_phase3.py` as the historical initial migration.

## Acceptance checklist on your machine

- Docker's Linux engine is reachable.
- `alembic current` reports `0001_phase3 (head)`.
- Both studio health cards connect; root stack checker succeeds.
- Fixture first run creates data, second run preserves it.
- Director query returns director + writer, while draft roster has eight distinct people.
- Snapshot inspection prints the same frozen input on repeated runs.
- Real PostgreSQL integration tests pass with no skipped integration cases.
- The original game still works at port 5500.

Then move to [Phase 4](../phase-04-handoff.md): real TMDB ingestion.
