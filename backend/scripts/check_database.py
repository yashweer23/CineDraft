"""Run from backend/: python -m scripts.check_database. Read-only SELECT 1."""
from pydantic import ValidationError

from app.config import Settings
from app.database import Database


def main():
    try:
        settings = Settings()
    except ValidationError:
        print("Invalid backend configuration. Run the root setup-env script and review backend/.env.")
        return 2
    db = Database(settings)
    try:
        if db.ping():
            print("PostgreSQL connected: SELECT 1 passed.")
            return 0
        print("PostgreSQL unavailable. Check the server, port and local credentials.")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
