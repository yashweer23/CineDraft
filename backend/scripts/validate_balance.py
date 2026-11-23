"""Paired synthetic drafting experiment. Run from backend; no API, DB or TMDB key."""
import argparse, csv, json, time
from pathlib import Path
from collections import defaultdict
from app.domain import GENRES, TIERS
from app.repository import canonical_hash
from app.validation.corpus import VERSION, STRATEGIES, catalog, draft
from app.validation.metrics import distribution, machine

def experiment(seeds):
    rows = []
    for genre in GENRES:
        for tier in TIERS:
            for index in range(seeds):
                seed = f'{VERSION}:seed:{index}'
                for strategy in STRATEGIES:
                    frozen,result,trace = draft(seed,genre,tier,strategy)
                    rows.append(dict(seed_index=index, genre=genre, tier=tier, strategy=strategy,
                        input_hash=canonical_hash(frozen.model_dump(mode='json')), output_hash=canonical_hash(result),
                        studio_score=result['studio_score'], studio_score_unrounded=result['studio_score_unrounded'],
                        profit_usd=result['profit_usd'], roi_percent=result['return_on_total_cost_percent'],
                        spend_usd=frozen.draft.budget.talent_spend_usd, unused_usd=result['unused_talent_budget_usd'],
                        selected='|'.join(t['selected'] for t in trace)))
    return rows

def summarize(rows):
    groups = defaultdict(list); pairs = defaultdict(dict)
    for r in rows:
        groups[r['genre'],r['tier'],r['strategy']].append(r)
        pairs[r['genre'],r['tier'],r['seed_index']][r['strategy']] = r
    cells = []
    for (genre,tier,strategy),values in sorted(groups.items()):
        cells.append(dict(genre=genre,tier=tier,strategy=strategy,
            **{metric:distribution([float(r[metric]) for r in values]) for metric in ('studio_score_unrounded','roi_percent','profit_usd','spend_usd')}))
    deltas=[]
    for genre in GENRES:
        for tier in TIERS:
            for strategy in STRATEGIES[1:]:
                matched=[v for (g,t,_),v in sorted(pairs.items()) if g==genre and t==tier]
                deltas.append(dict(genre=genre,tier=tier,strategy=strategy,reference='random',
                    **{metric:distribution([float(v[strategy][metric])-float(v['random'][metric]) for v in matched])
                       for metric in ('studio_score_unrounded','roi_percent','profit_usd')},
                    score_wins=sum(float(v[strategy]['studio_score_unrounded'])>float(v['random']['studio_score_unrounded']) for v in matched),
                    score_ties=sum(v[strategy]['studio_score_unrounded']==v['random']['studio_score_unrounded'] for v in matched)))
    return cells,deltas

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seeds',type=int,default=20);p.add_argument('--out',type=Path,default=Path('../validation-output/balance'))
    args=p.parse_args()
    if not 1<=args.seeds<=1000:p.error('--seeds must be 1..1000')
    started=time.perf_counter();rows=experiment(args.seeds);cells,deltas=summarize(rows);pool,profiles,_=catalog()
    report=dict(schema_version='phase13-balance-v1',synthetic=True,corpus_version=VERSION,
        seeds_per_cell=args.seeds,genres=list(GENRES),tiers=list(TIERS),strategies=list(STRATEGIES),
        runs=len(rows),people=len({t.person_id for t in pool}),person_roles=len(pool),
        row_hash=canonical_hash(rows),machine=machine(),elapsed_seconds=time.perf_counter()-started,
        method='Same catalog and seed per genre/tier/seed cell; three-card production offers, no rerolls or recasts; legal picks only; exact simulation replay checked for every run.',
        limits='Invented features and graph, production price formula. Equal-weight synthetic cells, not observed players or TMDB population. P10/P90 nearest rank describe sample variability, not confidence intervals. Different choices can change later offers. No rule tuning or balance certification.',
        cells=cells,paired_differences=deltas)
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'runs.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('runs','row_hash','elapsed_seconds','synthetic')},indent=2))
if __name__=='__main__':main()
