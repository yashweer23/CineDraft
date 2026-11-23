from alembic import context
from app.config import Settings
from app.database import Database
from app.models import Base

target_metadata = Base.metadata

def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    context.configure(url=Settings().database_url(), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    # Integration tests supply a transaction with a unique temporary schema.
    migrate(context.config.attributes["connection"])
else:
    db = Database(Settings())
    try:
        with db.engine.connect() as connection:
            migrate(connection)
    finally:
        db.close()
