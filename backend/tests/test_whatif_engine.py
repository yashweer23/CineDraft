from copy import deepcopy
from decimal import Decimal as D,localcontext
import pytest
from pydantic import ValidationError
from app.repository import canonical_hash
from app.whatif.engine import compare,quantile,seeds,SAMPLES
from app.whatif.example import example_inputs
from app.whatif.schemas import Inputs,CompareRequest
from app.simulation import engine as release


def test_original_person_control_has_exact_zero_in_every_paired_metric():
    value=compare(example_inputs(control=True))
    assert value['unchanged'] and value['score']['delta']==0
    for m in value['metrics']:
        assert m['baseline']==m['alternative']
        assert all(D(x)==0 for x in m['paired_delta'].values())
        assert (m['positive_samples'],m['equal_samples'],m['negative_samples'])==(0,64,0)


def test_replacement_is_reproducible_with_shared_seeds_and_no_input_mutation():
    inputs=example_inputs();before=inputs.model_dump(mode='json');value=compare(inputs)
    with localcontext() as ctx:
        ctx.prec=6
        assert compare(inputs)==value
    assert inputs.model_dump(mode='json')==before
    assert value['score']['baseline']==66 and value['score']['alternative']==68
    assert value['budget']['net_fee_change_usd']==43750
    assert value['sample_hash']==compare(example_inputs(control=True))['sample_hash']
    assert value['reproducibility']['sample_seeds']==seeds(inputs.source_input_hash)
    assert len(set(seeds(inputs.source_input_hash)))==SAMPLES
    assert value['sample_hash']!=canonical_hash(seeds('0'*64))


def test_pairing_matches_independent_manual_scenario_recomputation():
    inputs=example_inputs();value=compare(inputs)
    with localcontext() as ctx:
        ctx.prec=64
        vectors=[release.team_inputs(t) for t in (inputs.baseline,inputs.alternative)];deltas=[]
        for seed in seeds(inputs.source_input_hash):
            noise={name:release.draw(seed,name)['noise'] for name in release.MANIFEST['streams']}
            runs=[release.release_math(*v[:4],t.draft.budget.reserve_usd+t.draft.budget.talent_spend_usd,noise) for t,v in zip((inputs.baseline,inputs.alternative),vectors)]
            deltas.append(D(runs[1]['profit_usd'])-D(runs[0]['profit_usd']))
        metric=next(m for m in value['metrics'] if m['key']=='profit_usd')
        assert D(metric['paired_delta']['median'])==quantile(deltas,'.5')
        assert D(metric['paired_delta']['p10'])==quantile(deltas,'.1')
        assert metric['positive_samples']==sum(d>0 for d in deltas)


@pytest.mark.parametrize('p,expected',[('0',0),('.1',3),('.5',15),('.9',27),('1',30)])
def test_linear_quantiles(p,expected):assert quantile([30,0,20,10],p)==expected
@pytest.mark.parametrize('values,p',[([],'.5'),([1],'-1'),([1],'1.1')])
def test_invalid_quantiles(values,p):
    with pytest.raises(ValueError):quantile(values,p)


@pytest.mark.parametrize('kind',['manifest','two_slots','retained_profile','retained_card','unrelated_edge','duplicate','budget','fee','control'])
def test_rejects_inconsistent_hypothetical_inputs(kind):
    data=example_inputs(control=kind=='control').model_dump(mode='json');a=data['alternative']
    if kind=='manifest':data['manifest']['samples']=65
    if kind=='two_slots':a['draft']['picks'][1]['locked_fee_usd']+=1
    if kind=='retained_profile':a['role_features'][1]['attributes']['talent_strength']=1
    if kind=='retained_card':a['cards'][1]['name']='Changed retained person'
    if kind=='unrelated_edge':next(e for e in a['collaborations'] if 'director' not in [e['slot_a'],e['slot_b']])['message']='Changed unrelated evidence'
    if kind=='duplicate':a['draft']['picks'][0]['person_id']=a['draft']['picks'][1]['person_id']
    if kind=='budget':a['draft']['budget']['talent_remaining_usd']=-1
    if kind=='fee':a['cards'][0]['hiring_fee_usd']+=1
    if kind=='control':a['cards'][0]['name']='Altered original'
    with pytest.raises(ValueError):compare(data)


def test_hypothetical_team_has_no_historical_offers_or_live_revision():
    data=example_inputs().model_dump(mode='json');team=data['alternative']
    assert team['schema_version']=='phase11-team-v1'
    assert set(team['draft'])=={'genre_id','versions','budget','picks'}
    assert all(set(p)=={'slot','person_id','locked_fee_usd'} for p in team['draft']['picks'])
    with pytest.raises(ValidationError):Inputs.model_validate(data|{'seed':'client-choice'})
