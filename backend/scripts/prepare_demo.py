"""Build a fictional portfolio catalog; --activate explicitly changes the default for new drafts."""
import argparse,json,sys
from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy.exc import SQLAlchemyError
from app.config import Settings
from app.database import Database
from app.demo.catalog import preview
from app.demo.service import build

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group()
    group.add_argument('--preview',action='store_true',help='Calculate offline; no DB, settings or writes.')
    group.add_argument('--activate',action='store_true',help='Publish and activate this catalog for future drafts.')
    a=p.parse_args(argv);db=None
    try:
        if a.preview:result=preview()
        else:
            db=Database(Settings());result=build(db.engine,activate=a.activate)
        print(json.dumps(result,indent=2));return 0
    except (SettingsError,ValidationError,SQLAlchemyError):
        print('Demo setup failed. Check PostgreSQL, backend settings and migration head. Completed immutable stages are retained; rerun to resume.',file=sys.stderr);return 1
    except ValueError as e:print(str(e),file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
