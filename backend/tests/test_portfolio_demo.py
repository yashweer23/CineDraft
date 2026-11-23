from app.demo.catalog import records,observations,manifest,preview
from app.domain import GENRES,Slot,TIERS
from app.talent.calculation import build_features,build_prices
from app.drafting.assignment import Talent,legal_candidates
from app.drafting.rules import choose_offer


def test_demo_contains_observations_and_real_feature_price_graph_calculations():
    data=records();assert manifest(data)['input_rows_hash']=='b4ddd82610e63ee9de2a1b6a39c1bcd82365ece8c9d035e9924f0be58bc88394'
    assert len(data['people'])==36 and len(data['films'])==20 and len(data['credits'])==228
    assert all(p['name'].startswith('Synthetic ') for p in data['people'])
    assert len({(c['person_id'],c['role']) for c in data['credits']})==38
    features=build_features(*observations());assert all(len(p['evidence']['notable_works'])==5 for p in features['profiles'])
    assert set().union(*(set(f['genres']) for f in data['films']))==set(GENRES)
    result=preview();assert result==preview()
    assert result['graph_nodes']==38 and result['graph_edges']==341
    assert not result['tiers']['indie']['enabled'] and result['tiers']['studio']['enabled'] and result['tiers']['blockbuster']['enabled']
    assert result['minimum_assignment']['cost_usd']==28750000


def test_demo_has_complete_production_offers_and_affordable_alternatives():
    rows=build_prices(build_features(*observations())['profiles'])['rows'];pool=[Talent(r['person_id'],r['role'],r['fee_usd']) for r in rows]
    for tier in ('studio','blockbuster'):
        for seed in ('review:0','review:1','review:2'):
            available=TIERS[tier]*65//100;used=set();picks=[]
            for index,slot in enumerate(Slot):
                offers=choose_offer(legal_candidates(pool,slot,list(Slot)[index+1:],used,available),seed,f'pick:{slot.value}:{index}')
                chosen=next(r['talent'] for r in offers if r['selectable']);picks.append(chosen);used.add(chosen.person_id);available-=chosen.fee_usd
            assert len(used)==8 and available>=0
            if tier=='blockbuster':
                alternatives=legal_candidates(pool,Slot.DIRECTOR,[],used,available+picks[0].fee_usd)
                assert any(a['selectable'] for a in alternatives)


def test_worked_film_reconciles_and_its_director_swap_preserves_the_original():
    from scripts.portfolio_tour import tour
    from decimal import Decimal
    r=tour();x=r['release'];w=r['comparison'];e=r['evidence']
    assert len(r['choices'])==8 and len(r['first_card_works'])==5 and e['shared']==6 and e['bonus']==12
    assert sum(c['fee'] for c in r['choices'])+r['reserve']==x['production_cost_usd']
    assert x['profit_usd']==x['studio_receipts_usd']-x['production_cost_usd']-x['marketing_usd']
    assert w['samples']==64 and w['fee_delta']<0 and Decimal(w['profit_delta']['median'])<0 and r['replay_matched']
