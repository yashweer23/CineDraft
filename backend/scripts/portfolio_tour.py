"""One offline worked film: choose real offers, trace credits, release, then compare one swap."""
import argparse,json
from decimal import Decimal
from app.domain import Slot,SLOT_ROLES,TIERS
from app.demo.catalog import records,observations,identity,manifest
from app.talent.calculation import build_features,build_prices
from app.collaboration.calculation import build_graph,canonical_pair,edge_key,NO_SHARED
from app.drafting.assignment import Talent,legal_candidates
from app.drafting.rules import choose_offer,RELATIONSHIPS
from app.drafting.schemas import FrozenDraft
from app.simulation.example import synthetic_snapshot
from app.simulation.engine import simulate
from app.simulation.schemas import SimulationResult
from app.whatif.engine import project,compare,MANIFEST
from app.whatif.schemas import Inputs
from app.repository import canonical_hash

def tour():
    seed='portfolio-walkthrough-v1';genre='thriller';tier='blockbuster'
    data=records();films={r['id']:r for r in data['films']};names={r['id']:r['name'] for r in data['people']}
    observed=observations(data);features=build_features(*observed);prices=build_prices(features['profiles']);graph=build_graph(*observed)
    profiles={(r['person_id'],r['role']):r for r in features['profiles']};edges={r['edge_id']:r for r in graph['edges']}
    pool=[Talent(r['person_id'],r['role'],r['fee_usd']) for r in prices['rows']]
    picks=[];trace=[];used=set();remaining=TIERS[tier]*65//100
    for i,slot in enumerate(Slot):
        offers=choose_offer(legal_candidates(pool,slot,list(Slot)[i+1:],used,remaining),seed,f'pick:{slot.value}:{i}')
        choice=min((r['talent'] for r in offers if r['selectable']),key=lambda t:(-profiles[t.person_id,t.role]['attributes']['genre_fit'][genre],t.person_id))
        picks.append(choice);used.add(choice.person_id);remaining-=choice.fee_usd
        trace.append(dict(slot=slot.value,name=names[choice.person_id],fee=choice.fee_usd,remaining=remaining,
            offered=[dict(name=names[r['talent'].person_id],selectable=r['selectable']) for r in offers]))
    def freeze(selected):
        spend=sum(t.fee_usd for t in selected)
        f=synthetic_snapshot(seed=seed,tier=tier,spend=spend).model_dump(mode='json')
        f['draft'].update(genre_id=genre,draft_id=identity('tour-draft'))
        config={'synthetic':True,'scope':'offline portfolio tour','output_hash':graph['output_hash']};f['graph_configuration']=config
        versions=f['draft']['versions'];versions.update(dataset_id='fixture:portfolio-v1',catalog_id='fixture:offline-tour',
            feature_id='fixture:offline-tour-features',pricing_id='fixture:offline-tour-prices',graph_id='fixture:offline-tour-graph',
            role_mapping_version='fixture:portfolio-roles-v1',graph_hash=canonical_hash(config),catalog_hash=canonical_hash(manifest(data)),
            feature_hash=canonical_hash(features['profiles']),pricing_hash=canonical_hash(prices['rows']))
        roster={slot.value:t for slot,t in zip(Slot,selected)}
        for i,(slot,t) in enumerate(zip(Slot,selected)):
            p=profiles[t.person_id,t.role];a=p['attributes'];works=[]
            for w in p['evidence']['notable_works']:
                film=films[w['movie_id']];works.append(dict(movie_id=film['id'],title=film['title'],year=int(film['date'][:4]),
                    credited_jobs=w['credited_jobs'],poster_path=None,poster_url=None,audience_rating=float(film['rating']),vote_count=film['votes'],source='fixture'))
            f['draft']['picks'][i].update(person_id=t.person_id,locked_fee_usd=t.fee_usd,offer_id=identity('tour-offer:'+slot.value))
            f['cards'][i].update(person_id=t.person_id,name=names[t.person_id],versions=versions,hiring_fee_usd=t.fee_usd,
                talent_strength=a['talent_strength'],genre_fit=a['genre_fit'][genre],specialties=a['specialties'],coverage='Six fictional credited films',notable_works=works)
            f['role_features'][i]=p
        for e,(a,b) in zip(f['collaborations'],RELATIONSHIPS):
            left,right=canonical_pair(roster[a].person_id,roster[a].role,roster[b].person_id,roster[b].role);edge=edges.get(edge_key(left,right))
            e.update(canonical_a=list(left),canonical_b=list(right),edge_id=edge['edge_id'] if edge else None,shared_movie_count=edge['shared_movie_count'] if edge else 0,
                bonus=edge['bonus'] if edge else 0,evidence=edge['evidence'] if edge else [],message='Shared fictional credits.' if edge else NO_SHARED)
        return FrozenDraft.model_validate(f)
    frozen=freeze(picks);snapshot=canonical_hash(frozen.model_dump(mode='json'));result=SimulationResult.model_validate(simulate(frozen,snapshot)).model_dump(mode='json');official=canonical_hash(result)
    alternatives=[r['talent'] for r in legal_candidates(pool,Slot.DIRECTOR,[],used,remaining+picks[0].fee_usd) if r['selectable']]
    replacement=min(alternatives,key=lambda t:(t.fee_usd,t.person_id));baseline=project(frozen)
    pairs=compare(Inputs(draft_id=frozen.draft.draft_id,source_input_hash=snapshot,source_output_hash=official,slot='director',person_id=replacement.person_id,
        manifest=MANIFEST,baseline=baseline,alternative=project(freeze([replacement,*picks[1:]])),evidence_movies={mid:{'title':f['title'],'year':int(f['date'][:4])} for mid,f in films.items()}))
    source_again=canonical_hash(SimulationResult.model_validate(simulate(frozen,snapshot)).model_dump(mode='json'))
    if source_again!=official:raise ValueError('Original release changed during comparison')
    pair=max(result['explanation']['chemistry_edges'],key=lambda e:e['shared_movie_count']);e=pair['evidence'][0]
    return dict(mode='Offline worked example. Production algorithms, fictional source observations, no database writes.',genre=genre,tier=tier,
        budget=TIERS[tier],reserve=frozen.draft.budget.reserve_usd,spend=frozen.draft.budget.talent_spend_usd,choices=trace,
        first_card_works=[w.title for w in frozen.cards[0].notable_works],
        evidence=dict(a=names[pair['canonical_a'][0]],b=names[pair['canonical_b'][0]],shared=pair['shared_movie_count'],bonus=pair['bonus'],
            title=films[e['movie_id']]['title'],jobs_a=e['jobs_a'],jobs_b=e['jobs_b']),
        release={k:result[k] for k in ('studio_score','score_components','production_cost_usd','marketing_usd','worldwide_gross_usd','studio_receipts_usd','profit_usd')},
        comparison=dict(before=names[picks[0].person_id],after=names[replacement.person_id],samples=pairs['sample_count'],
            score_delta=pairs['score']['delta'],fee_delta=pairs['budget']['net_fee_change_usd'],
            profit_delta=next(m['paired_delta'] for m in pairs['metrics'] if m['key']=='profit_usd')),
        input_hash=snapshot,result_hash=official,replay_matched=official==source_again)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--json',action='store_true');a=p.parse_args();r=tour()
    if a.json:print(json.dumps(r,indent=2));return
    print(r['mode']);print('THRILLER / BLOCKBUSTER | $200M total, $70M reserve, $130M for talent')
    for choice in r['choices']:print(f"{choice['slot']:16} {choice['name']:34} ${choice['fee']:>12,}")
    e=r['evidence'];print(f"\nCREDITS: {e['a']} and {e['b']} share {e['shared']} films. Example: {e['title']} ({'/'.join(e['jobs_a'])}; {'/'.join(e['jobs_b'])}). Bonus: {e['bonus']}.")
    x=r['release'];print(f"RELEASE: {x['studio_score']}/100; fictional gross ${x['worldwide_gross_usd']:,}; profit ${x['profit_usd']:,}.")
    y=r['comparison'];print(f"WHAT-IF: {y['before']} -> {y['after']}; {y['samples']} paired scenarios; score change {y['score_delta']:+}; median fictional profit change ${Decimal(y['profit_delta']['median']):,.0f}.")
    print('Source result replays exactly:',r['replay_matched']);print('Full evidence: rerun with --json.')
if __name__=='__main__':main()
