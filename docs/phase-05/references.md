# References and implementation sources

The game formulas come from this project's [Phase 1 scoring design](../phase-01/scoring-design.md) and [talent data specification](../phase-01/talent-data-spec.md). They are project design choices, not ratings, prices or talent judgments supplied by TMDB.

Official technical documentation checked on 22 October 2026:

- [Python 3.12 Decimal](https://docs.python.org/3.12/library/decimal.html): decimal contexts, logarithms and half-up rounding.
- [SQLAlchemy 2.1 transactions](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html): transaction scopes and rollback behavior.
- [Phase 4 TMDB references](../phase-04/references.md): source metadata, images, credentials and attribution.

Runtime dependency pins were retained; checking current documentation did not upgrade packages. SQLAlchemy 2.1.5 remains the locked version. The standalone current API export is generated directly from the implemented FastAPI application.
