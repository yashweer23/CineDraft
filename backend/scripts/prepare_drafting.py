"""Prepare/activate a compatible catalog for new drafts; no upstream requests."""
import argparse,json,sys
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from pydantic_settings import SettingsError
from app.config import Settings
from app.database import Database
from app.drafting.catalog import prepare

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pricing',required=True);parser.add_argument('--graph',required=True)
    parser.add_argument('--version',required=True);parser.add_argument('--dry-run',action='store_true');parser.add_argument('--activate',action='store_true')
    args=parser.parse_args();db=None
    try:
        db=Database(Settings())
        result=prepare(db.engine,args.pricing,args.graph,args.version,dry_run=args.dry_run,activate=args.activate)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ValidationError,SettingsError):print('Invalid backend configuration; review backend/.env.',file=sys.stderr);return 1
    except ValueError as error:print(str(error),file=sys.stderr);return 1
    except SQLAlchemyError:print('Database operation failed. Check connectivity and migration head; uncommitted changes were rolled back.',file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
