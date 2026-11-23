"""Recompute a saved release from frozen inputs; read-only, no upstream requests."""
import argparse,json,sys
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from pydantic_settings import SettingsError
from app.config import Settings
from app.database import Database
from app.models import Result,DraftSnapshot
from app.repository import load_snapshot,canonical_hash
from app.simulation.engine import simulate
from app.simulation.schemas import SimulationResult


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--draft',required=True,type=UUID);args=parser.parse_args();db=None
    try:
        db=Database(Settings())
        with Session(db.engine) as s,s.begin():
            s.execute(text('SET TRANSACTION READ ONLY'))
            stored=s.get(Result,args.draft);snapshot=s.get(DraftSnapshot,args.draft)
            if stored is None or snapshot is None:raise ValueError('A finalized Phase 7 snapshot and saved Phase 8 result are required.')
            frozen=load_snapshot(s,args.draft)
            recomputed=SimulationResult.model_validate(simulate(frozen,snapshot.input_hash)).model_dump(mode='json')
            matched=stored.output_hash==canonical_hash(stored.outputs)==canonical_hash(recomputed) and stored.outputs==recomputed
            print(json.dumps({'draft_id':str(args.draft),'input_hash':snapshot.input_hash,'saved_output_hash':stored.output_hash,
                'recomputed_output_hash':canonical_hash(recomputed),'matched':matched,'writes':0,'upstream_requests':0},indent=2))
            return 0 if matched else 1
    except (ValidationError,SettingsError):print('Configuration or saved input/result schema is invalid. Check local settings and migration.',file=sys.stderr);return 1
    except ValueError as error:print(str(error),file=sys.stderr);return 1
    except SQLAlchemyError:print('Database read failed. Check connectivity and migration; no records were changed.',file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
