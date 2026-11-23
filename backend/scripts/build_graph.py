"""Build versioned collaboration evidence from a sealed local dataset; no TMDB requests."""
import argparse
import json
import sys
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from pydantic_settings import SettingsError
from app.config import Settings
from app.database import Database
from app.collaboration.service import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Sealed dataset ID, e.g. tmdb:first-import-v1")
    parser.add_argument("--version", required=True, help="Unique version label, e.g. first-graph-v1")
    parser.add_argument("--dry-run", action="store_true", help="Calculate and report without writes")
    args = parser.parse_args(); db = None
    try:
        db = Database(Settings())
        result = build(db.engine, args.dataset, args.version, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)); return 0
    except (ValidationError, SettingsError):
        print("Invalid backend configuration. Review backend/.env; credentials are not logged.", file=sys.stderr); return 1
    except ValueError as error:
        print(str(error), file=sys.stderr); return 1
    except SQLAlchemyError:
        print("Database operation failed. Check connectivity and Alembic head. Uncommitted changes were rolled back.", file=sys.stderr); return 1
    finally:
        if db: db.close()

if __name__ == "__main__": raise SystemExit(main())
