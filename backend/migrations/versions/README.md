# Schema history

| Revision | Addition | Domain tables after upgrade |
|---|---|---|
| 0001_phase3 | Frozen source snapshots and draft persistence | 21 |
| 0002_phase4 | Resumable import runs/resources | 23 |
| 0003_phase6 | Collaboration graph versions/nodes/edges/evidence | 27 |
| 0004_phase7 | Guest sessions, catalog activation and draft runtime | 31 |
| 0005_phase8 | Immutable simulation attempts | 32 |
| 0006_phase10 | Accounts, ownership, auth throttles and official challenges | 39 |

Counts exclude Alembic's own version table. Phase 5 used existing feature/pricing tables; Phase 9 required no migration.

Migrations contain frozen definitions and do not import live application models. Run `python -m alembic upgrade head` and `python -m alembic current` from `backend/` after configuring the database. Historical migrations are unchanged.

Phase 10 downgrade refuses once accounts or challenges exist, preserving ownership and competition history. Downgrade is reserved for isolated migration tests or a deliberate backup/restore plan; it is not a routine setup step. Static SQL/function parsing does not replace executing the PostgreSQL suite.
