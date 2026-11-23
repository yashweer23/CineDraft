"""Operator-only challenge publication. No public endpoint accepts a seed or catalog override."""
import argparse,json
from datetime import date
from app.config import Settings
from app.database import Database
from app.challenges.service import publish

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id',required=True);p.add_argument('--catalog',required=True)
    p.add_argument('--date',type=date.fromisoformat,required=True);p.add_argument('--timezone',default='Asia/Kolkata')
    p.add_argument('--genre',default='drama');p.add_argument('--tier',choices=['indie','studio','blockbuster'],default='indie');p.add_argument('--dry-run',action='store_true')
    a=p.parse_args();db=Database(Settings())
    try:print(json.dumps(publish(db.engine,a.id,a.catalog,a.date,a.timezone,a.genre,a.tier,dry_run=a.dry_run),default=str,indent=2))
    finally:db.close()
if __name__=='__main__':main()
