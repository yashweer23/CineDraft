import json
from sqlalchemy.orm import Session
from app.config import Settings
from app.database import Database
from app.fixtures import DRAFT_ID
from app.repository import load_snapshot

if __name__ == "__main__":
    db = Database(Settings())
    try:
        with Session(db.engine) as session:
            print(json.dumps(load_snapshot(session, DRAFT_ID).model_dump(mode="json"), indent=2))
    finally:
        db.close()
