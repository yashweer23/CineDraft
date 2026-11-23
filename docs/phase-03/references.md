# Implementation references

Reviewed 21 October 2026. These are technical references, not sources for fictional fixture data.

- PostgreSQL 17 constraints: https://www.postgresql.org/docs/17/ddl-constraints.html
- Alembic operation reference: https://alembic.sqlalchemy.org/en/latest/ops.html
- Alembic metadata comparison: https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html
- SQLAlchemy declarative tables: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- Docker Desktop startup on Windows: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Desktop troubleshooting: https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/

CineDraft-specific choices: immutable published datasets, separate source and game fields, composite identity/offer/price constraints, integer-dollar budgeting, and contracts ahead of engine implementation. PostgreSQL CHECK constraints apply to the current row; cross-table requirements use foreign keys or explicit triggers. Full action validation belongs in the future transactional service.
