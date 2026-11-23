"""Run with Python's standard library: python audit_demo.py PATH/TO/gameplay.sqlite"""
import argparse,sqlite3
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('database',type=Path);args=p.parse_args()
with sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True) as db:
    rows=db.execute(Path(__file__).with_name('audit-demo.sql').read_text()).fetchall()
for session,start,release in rows:print(f'{session} | {start} | {release or "(no official release)"}')
starts=len({r[1] for r in rows});completed=len({r[2] for r in rows if r[2]});print(f'{completed} releases / {starts} starts = {100*completed/starts:.1f}%' if starts else 'No synthetic demo starts found.')
