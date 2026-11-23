import csv,json
import pytest
from app.repository import canonical_hash
from scripts.validate_balance import experiment,summarize
from scripts.audit_balance import audit
from app.validation.corpus import VERSION

@pytest.fixture(scope='module')
def report_files(tmp_path_factory):
    folder=tmp_path_factory.mktemp('balance');rows=experiment(1);cells,pairs=summarize(rows)
    with (folder/'runs.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report=dict(corpus_version=VERSION,seeds_per_cell=1,row_hash=canonical_hash(rows),runs=len(rows),cells=cells,paired_differences=pairs)
    (folder/'report.json').write_text(json.dumps(report));return folder,report

def test_raw_csv_summaries_pairing_and_exact_replay_reconcile(report_files):
    folder,_=report_files;result=audit(folder,replay=True)
    assert result['runs']==90 and result['paired_comparisons_per_strategy']==30 and result['recomputed_drafts']

@pytest.mark.parametrize('damage',['raw','summary','coverage'])
def test_audit_catches_evidence_changes(report_files,tmp_path,damage):
    folder,original=report_files;report=json.loads(json.dumps(original));raw=(folder/'runs.csv').read_text()
    if damage=='raw':raw=raw.replace('genre_greedy','star_heavy',1)
    if damage=='summary':report['cells'][0]['profit_usd']['mean']+=1
    if damage=='coverage':report['seeds_per_cell']=2
    (tmp_path/'runs.csv').write_text(raw);(tmp_path/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError):audit(tmp_path)
