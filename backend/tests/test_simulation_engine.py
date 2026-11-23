from copy import deepcopy
from decimal import Decimal as D,localcontext
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.repository import canonical_hash
from app.simulation.engine import simulate,draw,score_components,release_math,dollars,MANIFEST_HASH,PRECISION,SimulationInputError
from app.simulation.example import synthetic_snapshot
from app.simulation.schemas import SimulationResult


def run(frozen=None):
    frozen=frozen or synthetic_snapshot();value=simulate(frozen,canonical_hash(frozen.model_dump(mode='json')))
    return SimulationResult.model_validate(value).model_dump(mode='json')


def test_known_arithmetic_separates_score_and_finance():
    components,raw,score=score_components(60,80,60,3250000,6500000)
    assert [D(c['contribution']) for c in components]==[D(18),D(24),D(15),D('8.925')]
    assert raw==D('65.925') and score==66
    release=release_math(60,80,60,50,6750000,{'critics':0,'audience':0,'revenue':0})
    assert D(release['critics_unrounded'])==70 and D(release['audience_unrounded'])==64
    assert D(release['gross_multiplier'])==D('2.752')
    assert release['worldwide_gross_usd']==18576000
    assert release['marketing_usd']==1350000 and release['studio_receipts_usd']==9288000
    assert release['profit_usd']==1188000 and release['total_cost_usd']==8100000
    with localcontext() as ctx:
        ctx.prec=PRECISION
        assert D(release['return_on_total_cost_percent'])==D(100)*1188000/8100000
    assert sum(release['weekly_gross_usd'])==18576000


def test_half_up_money_and_score_ties():
    assert [dollars(D(x)) for x in ('0.49','0.50','1.50','2.50')]==[0,1,2,3]
    # With no spend, all components equal 75 and the weighted result is exact.
    assert score_components(75,75,75,0,6500000)[2]==75
    r=release_math(0,0,60,0,3,{'critics':0,'audience':0,'revenue':0})
    assert r['marketing_usd']==1
    assert r['studio_receipts_usd']==dollars(D(r['worldwide_gross_usd'])/2)


def test_result_is_deterministic_and_named_streams_do_not_share_state():
    first=run();assert first==run()
    assert first['reproducibility']['manifest_hash']==MANIFEST_HASH
    expected=draw('stable','audience');draw('stable','critics',17);draw('other','revenue',99)
    assert draw('stable','audience')==expected
    assert draw('stable','audience')!=draw('stable','critics')
    assert run(synthetic_snapshot(seed='different'))['studio_score']==first['studio_score']
    assert run(synthetic_snapshot(seed='different'))['critics_unrounded']!=first['critics_unrounded']


@pytest.mark.parametrize('seed',[f'boundary-{i}' for i in range(25)])
def test_many_releases_reconcile_rounding_and_bounds(seed):
    r=run(synthetic_snapshot(seed=seed,talent=99,genre_fit=99,popularity=100,shared_films=4))
    assert 0<=r['critics']<=100 and 0<=r['audience']<=100 and 0<=r['studio_score']<=100
    assert r['profit_usd']==r['studio_receipts_usd']-r['total_cost_usd']
    assert r['total_cost_usd']==r['production_cost_usd']+r['marketing_usd']
    assert sum(r['weekly_gross_usd'])==r['worldwide_gross_usd'] and min(r['weekly_gross_usd'])>=0
    assert D('.4')<=D(r['weekly_retention'])<=D('.8')
    for record in r['reproducibility']['draws']:
        assert 0<=int(record['sample_uint53'])<2**53 and 0<=D(record['unit_interval'])<1
        assert abs(D(record['noise']))<=D('.6' if record['stream']=='revenue' else '5')


def test_full_precision_reviews_feed_gross_and_small_weekly_totals():
    noise={'critics':'0.0049','audience':'0.0049','revenue':0}
    r=release_math(60,80,60,50,100000000,noise)
    assert r['critics']==70 and r['audience']==64
    assert r['worldwide_gross_usd']==275213720  # Unrounded reviews, not displayed 70 and 64.
    for production in (1,2,3,7,11):
        r=release_math(0,0,60,0,production,{'critics':-5,'audience':-5,'revenue':'-.6'})
        assert sum(r['weekly_gross_usd'])==r['worldwide_gross_usd']
        assert r['weekly_gross_usd'][-1]>=0 and r['profit_usd']<0


def test_chemistry_is_neutral_without_evidence_and_caps_at_three_films():
    zero=run();three=run(synthetic_snapshot(shared_films=3));six=run(synthetic_snapshot(shared_films=6))
    assert D(zero['score_components'][2]['value'])==60
    assert D(three['score_components'][2]['value'])==100
    assert three['score_components']==six['score_components']
    assert len(six['explanation']['chemistry_edges'])==12
    assert all(len(e['evidence'])==6 and e['bonus']==12 for e in six['explanation']['chemistry_edges'])


def test_missing_popularity_uses_neutral_appeal_but_zero_is_observed_zero():
    missing=run(synthetic_snapshot(popularity=None));zero=run(synthetic_snapshot(popularity=0))
    assert D(missing['cast_appeal'])==50 and D(zero['cast_appeal'])==0
    assert len(missing['explanation']['warnings'])==4
    assert missing['studio_score']==zero['studio_score']  # Popularity is not a direct score component.


def test_weights_top_contributors_coverage_and_unused_money_are_explained():
    r=run();assert r['explanation']['top_genre_contributors']==['director','writer']
    assert len(r['explanation']['rows'])==8 and r['unused_talent_budget_usd']==3250000
    f=synthetic_snapshot();f.role_features[0].attributes['coverage']['level']='low';f.role_features[0].evidence['genre_catalog_gaps']=['drama']
    warnings=run(f)['explanation']['warnings'];assert any('low source coverage' in w for w in warnings) and any('catalog gap' in w for w in warnings)


@pytest.mark.parametrize('scenario',['hash','configuration','profile','card','edges','bonus','evidence','self_pair','version','graph_hash'])
def test_tampered_or_unsupported_inputs_are_rejected(scenario):
    f=synthetic_snapshot(shared_films=1)
    if scenario=='configuration':f.scoring_configuration=deepcopy(f.scoring_configuration)|{'changed':True}
    if scenario=='profile':f.role_features[0].attributes['talent_strength']=101
    if scenario=='card':f.cards[0].talent_strength=79
    if scenario=='edges':f.collaborations[0],f.collaborations[1]=f.collaborations[1],f.collaborations[0]
    if scenario=='bonus':f.collaborations[0]['bonus']=12
    if scenario=='evidence':f.collaborations[0]['evidence']=[]
    if scenario=='self_pair':f.collaborations[0]['canonical_a']=f.collaborations[0]['canonical_b']
    if scenario=='version':f.draft.versions.simulation_version='unsupported'
    if scenario=='graph_hash':f.graph_configuration={'changed':True}
    digest='0'*64 if scenario=='hash' else canonical_hash(f.model_dump(mode='json'))
    with pytest.raises(SimulationInputError):simulate(f,digest)


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),'NaN','Infinity',-1,101])
def test_invalid_numeric_inputs_do_not_silently_become_scores(bad):
    with pytest.raises(SimulationInputError):score_components(bad,80,60,100,1000)


def test_result_schema_rejects_broken_score_and_financial_reconciliation():
    r=run()
    for changes in ({'studio_score':0},{'profit_usd':0},{'total_cost_usd':1},{'weekly_gross_usd':[0,0,0,0]},{'return_on_total_cost_percent':'0'}):
        with pytest.raises(ValidationError):SimulationResult.model_validate(r|changes)


def test_result_schema_export_matches_current_model():
    saved=json.loads((Path(__file__).resolve().parents[2]/'contracts/result.phase8.schema.json').read_text())
    assert saved==SimulationResult.model_json_schema()

def test_random_stream_golden_vector_pins_cross_run_mapping():
    value=draw('stable','critics')
    assert value['sha256']=='a3847f78250d31d48252f73eacdba5bf54429771222e02f32f85efcd55c3d26d'
    assert value['sample_uint53']=='5753263026905510'
    assert D(value['noise'])==D('1.387405079195118684509679951588623225688934326171875')


def test_external_decimal_precision_does_not_change_saved_output():
    expected=run()
    with localcontext() as ctx:
        ctx.prec=6;ctx.rounding='ROUND_FLOOR'
        assert run()==expected
