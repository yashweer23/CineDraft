# Local release runbook

Run from the extracted project root, in PowerShell, with Docker Desktop running Linux containers. Preserve the original Compose project name and database volume on upgrade. Phase 14 adds no migration. `docker compose down -v` is not an upgrade or recovery step.

## Diagnose a failed startup

```powershell
docker compose ps
docker compose logs --tail 60 db api web
Invoke-RestMethod http://127.0.0.1:8001/api/health
Invoke-RestMethod http://127.0.0.1:8001/api/health/ready
npm run check:stack
```

| Observation | What it tells you | Next move |
|---|---|---|
| API health responds; readiness returns 503 | API is running; the PostgreSQL probe failed | Check the db container and native vs container port/credentials. |
| Both API checks pass; studio cannot connect | The proxy or frontend host port may be wrong | Confirm `WEB_PORT=5174`, `API_PORT=8001`, and native `API_PROXY_TARGET=http://127.0.0.1:8001`. |
| Studio reports no active catalog | Database connectivity alone does not make a game playable | Build a review catalog; choose activation only if you want it to become the default. |
| Old module/CLI missing after merge | Scripts and migrations are copied into the API image | Rebuild `api` and `api-tests`; an app-source bind mount does not update scripts. |
| A command appears to have failed after submit | The server may already have committed it | Use the studio's same-request retry. Inspect the saved film before issuing a different command. |

Unhandled API failures log a server-generated request ID. Responses include `X-Request-ID`; the error envelope contains its matching ID. Retain that ID, timestamp and operation when diagnosing an error. Do not paste recovery tokens, passwords, full owner exports, database dumps or `.env` files into issue reports. `/api/health/ready` checks connectivity, not migration head, catalog readiness or an entire game journey.

## Back up before merging or migrating

With the existing `db` service healthy, choose a new local filename. The helper uses the container's `pg_dump`, sends custom-format binary output directly to a file, and refuses to overwrite existing files. The source release excludes `backups/`, `*.dump` and local environment files.

```powershell
node scripts/backup-db.cjs --out backups/pre-phase14-01.dump
Get-FileHash .\backups\pre-phase14-01.dump -Algorithm SHA256
```

An archive header and successful process exit are only initial checks. Keep the dump and environment/credentials separately in private storage. The dump covers the configured database; it does not capture the entire PostgreSQL cluster, global roles, external credentials or the optional local SQLite analysis copy.

## Restore drill into a new database

Use only a dump you created and trust. Run each line separately and continue **only on success** (`$LASTEXITCODE -eq 0`). The example target name `cinedraft_restore_review` must be fresh and different from your running game database. `createdb` failing because the target exists is a stop condition; choose a different new name in every following command. Keep the live API pointed at its original database.

```powershell
docker compose cp .\backups\pre-phase14-01.dump db:/tmp/cinedraft-phase14-review.dump
docker compose exec -T db pg_restore --list /tmp/cinedraft-phase14-review.dump
docker compose exec -T db sh -c 'createdb --username="$POSTGRES_USER" --template=template0 cinedraft_restore_review'
docker compose exec -T db sh -c 'pg_restore --username="$POSTGRES_USER" --dbname=cinedraft_restore_review --no-owner --no-privileges --exit-on-error --single-transaction /tmp/cinedraft-phase14-review.dump'
docker compose exec -T db sh -c 'psql --username="$POSTGRES_USER" --dbname=cinedraft_restore_review -v ON_ERROR_STOP=1 -c "SELECT version_num FROM alembic_version"'
docker compose run --rm -e DB_NAME=cinedraft_restore_review api python -m scripts.check_database
```

For a Phase 12–14 source database, expect `0008_phase12`. Older backups should show their **original** migration head before any upgrade. Compare counts of `drafts`, `picks`, `draft_snapshots`, `results` and `whatif_analyses` on source and restored copy, using a quiet source to avoid concurrent changes. For a known released film run `docker compose run --rm -e DB_NAME=cinedraft_restore_review api python -m scripts.verify_release --draft YOUR-RELEASED-UUID`. Replace the placeholder; look for `matched: true`. Verify a known comparison with `scripts.verify_whatif --analysis YOUR-ANALYSIS-UUID` the same way. Record the archive hash, head, counts and verifier results before calling the backup tested. Keep or remove the isolated restore database according to your own retention needs; this guide never drops a database.

Reference: PostgreSQL 17 [pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html). The backup wrapper was tested with simulated subprocess output here. A live dump/restore drill was not run in this build environment.
