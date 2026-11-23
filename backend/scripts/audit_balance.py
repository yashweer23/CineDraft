"""Reconcile raw balance CSV with its manifest, summaries and paired denominators."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
from app.domain import GENRES,TIERS
from app.repository import canonical_hash
from app.validation.corpus import STRATEGIES,VERSION
from scripts.validate_balance import summarize,experiment

INTEGER_FIELDS=('seed_index','studio_score','profit_usd','spend_usd','unused_usd')

def audit(directory,*,replay=False):
    report=json.loads((directory/'report.json').read_text(encoding='utf-8'))
    with (directory/'runs.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    for row in rows:
        for key in INTEGER_FIELDS:row[key]=int(row[key])
    if report['corpus_version']!=VERSION or canonical_hash(rows)!=report['row_hash']:raise ValueError('Corpus version or row hash does not match')
    n=report['seeds_per_cell']
    if type(n) is not int or not 1<=n<=1000:raise ValueError('Invalid seed count')
    expected={(g,t,s,i) for g in GENRES for t in TIERS for s in STRATEGIES for i in range(n)}
    observed=Counter((r['genre'],r['tier'],r['strategy'],r['seed_index']) for r in rows)
    if set(observed)!=expected or any(v!=1 for v in observed.values()) or len(rows)!=report['runs']:raise ValueError('Experiment coverage or pairing is incomplete')
    cells,deltas=summarize(rows)
    if cells!=report['cells'] or deltas!=report['paired_differences']:raise ValueError('Summaries do not reconcile with raw rows')
    if replay and rows!=experiment(n):raise ValueError('Production-engine replay differs from evidence')
    return dict(matched=True,runs=len(rows),paired_comparisons_per_strategy=n*len(GENRES)*len(TIERS),
        row_hash=report['row_hash'],recomputed_drafts=replay,synthetic=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--replay',action='store_true');a=p.parse_args()
    print(json.dumps(audit(a.directory,replay=a.replay),indent=2))
if __name__=='__main__':main()
