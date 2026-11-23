"""Local, explicit TMDB ingestion. No import runs on API startup."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
from uuid import UUID
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.config import Settings
from app.database import Database
from app.tmdb.client import TMDBClient, TMDBError
from app.tmdb.importer import (new_run, collect, review, publish, run_info, exclusive_import, ImportProblem)

def parser():
    root=argparse.ArgumentParser(description=__doc__)
    sub=root.add_subparsers(dest="command",required=True)
    start=sub.add_parser("start",help="Create a checkpointed import run (does not publish)")
    start.add_argument("--dataset",required=True,help="New version label, e.g. first-import-v1")
    start.add_argument("--ids",type=int,nargs="+",help="Explicit actual TMDB movie IDs; otherwise use discovery")
    start.add_argument("--pages",type=int,default=1)
    start.add_argument("--max-movies",type=int,default=20)
    start.add_argument("--cutoff",type=date.fromisoformat)
    for name in ["resume","status","review","publish"]:
        cmd=sub.add_parser(name);cmd.add_argument("--run",type=UUID,required=True)
        if name in ("review","publish"):cmd.add_argument("--reviews",type=Path,help="JSON object of source movie ID to manual review")
    sub.add_parser("smoke",help="Opt-in live configuration request; no database writes")
    return root

def main():
    args=parser().parse_args();db=None;client=None
    try:
        settings=Settings()
        if args.command in ("start","resume","smoke"):
            client=TMDBClient(settings.tmdb_read_access_token.get_secret_value())
        if args.command=="smoke":
            from app.tmdb.payloads import ConfigurationPayload
            value=ConfigurationPayload.model_validate(client.configuration())
            print(json.dumps({"tmdb":"reachable","configuration_valid":True,"poster_sizes":value.images.poster_sizes}))
            return 0
        db=Database(settings)
        overrides=None
        if getattr(args,"reviews",None):
            overrides=json.loads(args.reviews.read_text(encoding="utf-8"))
            if not isinstance(overrides,dict):raise ImportProblem("Reviews file must be a JSON object")
        if args.command=="status":
            result=run_info(db.engine,args.run)
        else:
            with exclusive_import(db.engine):
                if args.command=="start":
                    run_id=new_run(db.engine,args.dataset,ids=args.ids,pages=args.pages,max_movies=args.max_movies,cutoff=args.cutoff)
                    # Flush the run ID before networking: the user can resume even if the first request fails.
                    print(json.dumps({"run_id":str(run_id),"next":"Save this ID to resume, review and publish"}),flush=True)
                    result=collect(db.engine,run_id,client)
                elif args.command=="resume":result=collect(db.engine,args.run,client)
                elif args.command=="review":result=review(db.engine,args.run,overrides)
                else:result=publish(db.engine,args.run,overrides)
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (TMDBError,ImportProblem) as error:
        print(str(error),file=sys.stderr);return 1
    except (ValidationError,ValueError,TypeError,OSError):
        print("Configuration, review file or upstream data is invalid. Check the documented format; no input values are logged.",file=sys.stderr);return 1
    except SQLAlchemyError:
        print("Database operation failed. Check connection and run Alembic upgrade head. Uncommitted publication changes were rolled back.",file=sys.stderr);return 1
    finally:
        if client:client.close()
        if db:db.close()

if __name__=="__main__":raise SystemExit(main())
