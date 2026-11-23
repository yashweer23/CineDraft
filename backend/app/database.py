from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings


class Database:
    def __init__(self, settings: Settings):
        self.engine = create_engine(
            settings.database_url(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=0,
            pool_timeout=3,
            connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
            hide_parameters=True,
        )

    def ping(self) -> bool:
        """Use PostgreSQL itself, without creating any application tables."""
        try:
            with self.engine.connect() as connection:
                return connection.execute(text("SELECT 1")).scalar_one() == 1
        except SQLAlchemyError:
            # Do not expose a DSN, password, driver message or server details.
            return False

    def close(self) -> None:
        self.engine.dispose()
