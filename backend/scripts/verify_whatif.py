"""Recompute a hypothetical report with a read-only database transaction."""
import argparse,json,sys
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from pydantic_settings import SettingsError
from app.config import Settings
from app.database import Database
from app.models import WhatIfAnalysis,Result,DraftSnapshot
from app.repository import canonical_hash
from app.whatif.engine import compare
from app.whatif.service import checked
from app.drafting.errors import DraftProblem

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--analysis',required=True,type=UUID);args=parser.parse_args();db=None
    try:
        db=Database(Settings())
        with Session(db.engine) as s,s.begin():
            s.execute(text('SET TRANSACTION READ ONLY'));stored=s.get(WhatIfAnalysis,args.analysis)
            if stored is None:raise ValueError('Hypothetical report not found.')
            checked(stored);source=s.get(Result,stored.draft_id);snapshot=s.get(DraftSnapshot,stored.draft_id)
            value=compare(stored.inputs);digest=canonical_hash(value)
            matched=bool(source and snapshot and source.input_hash==snapshot.input_hash==stored.source_input_hash and source.output_hash==stored.source_output_hash==canonical_hash(source.outputs) and digest==stored.output_hash and value==stored.outputs)
            print(json.dumps(dict(analysis_id=str(args.analysis),matched=matched,saved_output_hash=stored.output_hash,recomputed_output_hash=digest,writes=0,upstream_requests=0),indent=2));return 0 if matched else 1
    except (ValidationError,SettingsError,DraftProblem):print('Configuration or stored report is invalid. Check settings and migration.',file=sys.stderr);return 1
    except ValueError as e:print(str(e),file=sys.stderr);return 1
    except SQLAlchemyError:print('Database read failed; no records changed.',file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
