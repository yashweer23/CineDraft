"""Build a private, offline BI dashboard from invented data or owner-exported films."""
import argparse,json,sqlite3,sys
from pathlib import Path
from datetime import datetime,timezone
from pydantic import ValidationError
from app.analytics.mart import open_mart,ingest,report
from app.analytics.dashboard import render
from app.analytics.demo import streams

def instant(s):
    try:
        dt=datetime.fromisoformat(s.replace('Z','+00:00'))
        if len(s)==10:return dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:raise ValueError
        return dt
    except ValueError:raise argparse.ArgumentTypeError('Use YYYY-MM-DD (00:00 UTC) or an ISO timestamp with an offset.') from None

def save(result,out):
    out.mkdir(parents=True,exist_ok=True);(out/'dashboard.html').write_text(render(result),encoding='utf-8');(out/'metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(f"{result['filters']['cohort']}: {result['overview'][0]['completed']} official releases / {result['overview'][0]['started']} starts. Open {out/'dashboard.html'}")

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo',help='Create the reproducible twelve-film synthetic cohort and report.');demo.add_argument('--out',type=Path,default=Path('analytics-output/demo'))
    imp=sub.add_parser('import',help='Import one film exported by its owner. Older snapshots or changed evidence are rejected.');imp.add_argument('file',type=Path);imp.add_argument('--db',type=Path,required=True);imp.add_argument('--cohort',choices=['internal','playtest'],default='internal');imp.add_argument('--observed-human',action='store_true')
    rep=sub.add_parser('report');rep.add_argument('--db',type=Path,required=True);rep.add_argument('--out',type=Path,required=True);rep.add_argument('--cohort',required=True,choices=['demo','internal','playtest']);rep.add_argument('--from',dest='start',type=instant);rep.add_argument('--until',type=instant);rep.add_argument('--as-of',type=instant);rep.add_argument('--mode',choices=['practice','closed_challenge']);rep.add_argument('--fixture',choices=['yes','no'])
    for f in ['genre','tier','catalog','rules','scoring','simulation']:rep.add_argument('--'+f)
    a=p.parse_args(argv);db=None
    try:
        if a.command=='demo':
            a.out.mkdir(parents=True,exist_ok=True);db=open_mart(a.out/'gameplay.sqlite');
            for s in streams():ingest(db,s,'demo')
            save(report(db,group='demo',as_of=instant('2026-11-01')),a.out)
        elif a.command=='import':
            if a.file.stat().st_size>16*1024*1024:raise ValueError('Export exceeds 16 MiB per film.')
            x=json.loads(a.file.read_text(encoding='utf-8-sig'));a.db.parent.mkdir(parents=True,exist_ok=True);db=open_mart(a.db);print(json.dumps(ingest(db,x,a.cohort,observed=a.observed_human)))
        else:
            if not a.db.is_file():raise ValueError('Local database not found. Run demo or import first.')
            db=open_mart(a.db,readonly=True);result=report(db,group=a.cohort,as_of=a.as_of or datetime.now(timezone.utc),start=a.start,until=a.until,genre=a.genre,tier=a.tier,catalog=a.catalog,rules=a.rules,scoring=a.scoring,simulation=a.simulation,mode=a.mode,fixture=None if a.fixture is None else int(a.fixture=='yes'));save(result,a.out)
        return 0
    except ValidationError:print('Invalid gameplay export schema. No events were imported.',file=sys.stderr);return 1
    except (ValueError,OSError,sqlite3.Error) as e:print(f'Analytics operation failed: {e}',file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
