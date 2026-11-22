# CineDraft backend — Phase 10

Python 3.12, FastAPI, SQLAlchemy, PostgreSQL and Alembic. Follow the [root README](../README.md) for Docker/PowerShell setup, account lifecycle and ports 5433/8001/5174. Current migration head: `0006_phase10` (39 tables); API 0.10.0. Earlier migrations, catalogs, snapshots and fixture results remain preserved.

From `backend/`, using the virtual environment and private configuration:

```sh
python -m alembic upgrade head
python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8001
```

The Phase 7 guide covers compatible catalog preparation; existing catalogs need no rebuild. Account and challenge implementations are in `app/accounts/` and `app/challenges/`. Challenge publication and password recovery are explicit operator CLIs, not startup side effects. See the [Phase 10 API](../docs/phase-10/api.md) and [design](../docs/phase-10/design.md).

The pure engine remains `app/simulation/engine.py`. `app/simulation/service.py` authorizes account/guest owners, embargoes open-challenge reports and writes official submissions atomically. `python -m scripts.verify_release --draft UUID` is a read-only **trusted operator** replay, not a public endpoint. An operator can inspect private seeds; keep that authority separate from participant accounts.

`python -m scripts.simulation_example` needs no database or token. `python -m pytest -q -m 'not integration'` runs the unit suite; `python -m scripts.run_integration` uses `backend/.env` for real PostgreSQL tests in isolated schemas. PostgreSQL execution was unavailable during packaging. Check the [verification record](../docs/phase-10/verification.md) for exact observed counts and remaining gates.

`python -m scripts.export_phase10_contracts` exports current OpenAPI plus Phase 10 schemas without connecting to the database or rewriting Phase 7/8 schema artifacts. Frozen scoring, arithmetic and stream versions remain documented in [Phase 8](../docs/phase-08/design.md).
