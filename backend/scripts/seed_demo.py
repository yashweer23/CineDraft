"""Opt-in local fixture. Re-running preserves the first complete copy."""
import json
from sqlalchemy.orm import Session
from app.config import Settings
from app.database import Database
from app.fixtures import seed_fixture

def main():
    db = Database(Settings())
    try:
        with Session(db.engine) as session, session.begin():
            result = seed_fixture(session)
        print(json.dumps(result, indent=2))
    finally:
        db.close()

if __name__ == "__main__":
    main()
