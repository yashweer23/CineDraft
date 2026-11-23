"""Bounded paired scenarios reusing Phase 8 arithmetic without writing official results."""
from decimal import Decimal as D,localcontext,ROUND_HALF_UP
from app.repository import canonical_hash
from app.simulation import engine as release
from app.drafting.rules import RULES_ID,SCORING_ID,SIMULATION_VERSION
from app.whatif import schemas as w
VERSION='whatif-1.0'
SAMPLES=64
MANIFEST={'version':VERSION,'engine_manifest_hash':release.MANIFEST_HASH,'samples':SAMPLES,
    'sample_seed':'SHA256 canonical JSON [whatif-1.0, source_input_hash, sample_index]; indices 0..63',
    'pairing':'same three named Phase 8 noise draws for both teams in each scenario',
    'quantiles':'linear interpolation at (n-1)*p; p=0.1,0.5,0.9',
    'deltas':'alternative minus baseline within each scenario, then summarize',
    'reviews':'unrounded Decimal values; financial dollar rounding inherited from simulation-1.0',
    'arithmetic':'Decimal precision 64; ROUND_HALF_UP','official_results_unchanged':True}
METRICS=[('critics_unrounded','Critics','points'),('audience_unrounded','Audience','points'),('worldwide_gross_usd','Worldwide gross','USD'),('profit_usd','Profit','USD'),('return_on_total_cost_percent','Return on total cost','percent')]

def project(frozen):
    return w.Team(synthetic=frozen.synthetic,draft=dict(genre_id=frozen.draft.genre_id,versions=frozen.draft.versions,budget=frozen.draft.budget,
        picks=[dict(slot=p.slot,person_id=p.person_id,locked_fee_usd=p.locked_fee_usd) for p in frozen.draft.picks]),
        cards=frozen.cards,role_features=frozen.role_features,graph_configuration=frozen.graph_configuration,collaborations=frozen.collaborations)

def quantile(values,p):
    if not values:raise ValueError('Empty scenario sample.')
    if not D(0)<=D(p)<=D(1):raise ValueError('Quantile must be between zero and one.')
    values=sorted(map(D,values));position=D(len(values)-1)*D(p);i=int(position);fraction=position-i
    return values[i]+fraction*(values[min(i+1,len(values)-1)]-values[i])

def distribution(values):
    return {key:release.exact(quantile(values,p)) for key,p in [('p10','.1'),('median','.5'),('p90','.9')]}

def seeds(source_hash):return [canonical_hash([VERSION,source_hash,i]) for i in range(SAMPLES)]

def validate(inputs):
    if inputs.manifest!=MANIFEST:raise ValueError('Unsupported what-if manifest.')
    b,a=inputs.baseline,inputs.alternative
    if a.synthetic!=b.synthetic or a.draft.versions!=b.draft.versions or a.draft.genre_id!=b.draft.genre_id:raise ValueError('Paired teams must share source versions, genre and synthetic marker.')
    v=b.draft.versions
    if (v.rules_id,v.scoring_id,v.simulation_version)!=(RULES_ID,SCORING_ID,SIMULATION_VERSION):raise ValueError('Unsupported source engine versions.')
    for team in (b,a):
        if canonical_hash(team.graph_configuration)!=v.graph_hash:raise ValueError('Graph manifest does not match.')
    bp={p.slot:p for p in b.draft.picks};ap={p.slot:p for p in a.draft.picks}
    if ap[inputs.slot].person_id!=inputs.person_id:raise ValueError('Replacement identity does not match the request.')
    for slot in bp:
        if slot!=inputs.slot and ap[slot]!=bp[slot]:raise ValueError('Only one slot may change.')
    for key in ('tier','currency','total_budget_usd','reserve_usd','talent_budget_usd'):
        if getattr(a.draft.budget,key)!=getattr(b.draft.budget,key):raise ValueError('The original budget allocation must remain fixed.')
    bcards={c.person_id:c for c in b.cards};acards={c.person_id:c for c in a.cards}
    bf={(f.person_id,f.role):f for f in b.role_features};af={(f.person_id,f.role):f for f in a.role_features}
    for slot,p in bp.items():
        if slot!=inputs.slot and (bcards[p.person_id]!=acards[p.person_id] or any(af.get(k)!=f for k,f in bf.items() if k[0]==p.person_id)):raise ValueError('Retained profiles must not change.')
    for before,after in zip(b.collaborations,a.collaborations):
        if inputs.slot.value not in (before.get('slot_a'),before.get('slot_b')) and before!=after:raise ValueError('Unchanged relationships must retain their evidence.')
    unchanged=ap[inputs.slot].person_id==bp[inputs.slot].person_id
    if unchanged and a!=b:raise ValueError('The original pick must be an exact control.')
    return unchanged

def compare(inputs):
    inputs=w.Inputs.model_validate(inputs);unchanged=validate(inputs)
    with localcontext() as ctx:
        ctx.prec=64;ctx.rounding=ROUND_HALF_UP
        teams=[inputs.baseline,inputs.alternative];vectors=[release.team_inputs(t) for t in teams]
        scores=[release.score_components(*v[:3],t.draft.budget.talent_spend_usd,t.draft.budget.talent_budget_usd) for t,v in zip(teams,vectors)]
        sample=seeds(inputs.source_input_hash);runs=[[],[]]
        for seed in sample:
            noise={name:release.draw(seed,name)['noise'] for name in release.MANIFEST['streams']}
            for i,(t,v) in enumerate(zip(teams,vectors)):
                runs[i].append(release.release_math(*v[:4],t.draft.budget.reserve_usd+t.draft.budget.talent_spend_usd,noise))
        metrics=[]
        for key,label,unit in METRICS:
            before=[D(str(r[key])) for r in runs[0]];after=[D(str(r[key])) for r in runs[1]];delta=[a-b for a,b in zip(after,before)]
            metrics.append(dict(key=key,label=label,unit=unit,baseline=distribution(before),alternative=distribution(after),paired_delta=distribution(delta),
                positive_samples=sum(x>0 for x in delta),equal_samples=sum(x==0 for x in delta),negative_samples=sum(x<0 for x in delta)))
        rows=[next(r for r in v[4] if r['slot']==inputs.slot.value) for v in vectors]
        changed=[]
        for before,after in zip(vectors[0][5],vectors[1][5]):
            if inputs.slot.value not in (before['slot_a'],before['slot_b']):continue
            def enrich(edge):
                value=dict(edge)
                value['evidence']=[dict(e,**inputs.evidence_movies.get(e['movie_id'],{'title':'Title unavailable','year':None})) for e in edge['evidence']]
                return value
            changed.append(dict(slot_a=before['slot_a'],slot_b=before['slot_b'],before=enrich(before),after=enrich(after),bonus_delta=after['bonus']-before['bonus']))
        cards=[next(c for c in t.cards if c.person_id==next(p.person_id for p in t.draft.picks if p.slot==inputs.slot)) for t in teams]
        budget=dict(refund_usd=cards[0].hiring_fee_usd,replacement_fee_usd=cards[1].hiring_fee_usd,
            net_fee_change_usd=cards[1].hiring_fee_usd-cards[0].hiring_fee_usd,baseline_spend_usd=teams[0].draft.budget.talent_spend_usd,
            alternative_spend_usd=teams[1].draft.budget.talent_spend_usd,alternative_remaining_usd=teams[1].draft.budget.talent_remaining_usd,
            reserve_usd=teams[0].draft.budget.reserve_usd,baseline_production_usd=runs[0][0]['production_cost_usd'],alternative_production_usd=runs[1][0]['production_cost_usd'],
            baseline_marketing_usd=runs[0][0]['marketing_usd'],alternative_marketing_usd=runs[1][0]['marketing_usd'])
        components=[dict(name=b['name'],baseline=b['contribution'],alternative=a['contribution'],delta=release.exact(D(a['contribution'])-D(b['contribution']))) for b,a in zip(scores[0][0],scores[1][0])]
        result=dict(version=VERSION,draft_id=inputs.draft_id,source_input_hash=inputs.source_input_hash,source_output_hash=inputs.source_output_hash,
            sample_count=SAMPLES,sample_hash=canonical_hash(sample),unchanged=unchanged,synthetic=inputs.baseline.synthetic,slot=inputs.slot,
            baseline_card=cards[0],alternative_card=cards[1],budget=budget,metrics=metrics,
            score=dict(baseline=scores[0][2],alternative=scores[1][2],delta=scores[1][2]-scores[0][2],unrounded_delta=release.exact(scores[1][1]-scores[0][1]),components=components),
            explanation=dict(baseline_row=rows[0],alternative_row=rows[1],chemistry_before=release.exact(vectors[0][2]),chemistry_after=release.exact(vectors[1][2]),
                chemistry_delta=release.exact(vectors[1][2]-vectors[0][2]),relationships=changed,baseline_warnings=vectors[0][6],alternative_warnings=vectors[1][6],
                note='Hypothetical game scenarios, not real-world predictions. P10–P90 describes simulated outcomes, not a confidence interval. Paired median differences need not equal the difference of two medians.'),
            reproducibility=dict(manifest=MANIFEST,manifest_hash=canonical_hash(MANIFEST),sample_seeds=sample,baseline_team_hash=canonical_hash(inputs.baseline.model_dump(mode='json')),alternative_team_hash=canonical_hash(inputs.alternative.model_dump(mode='json'))))
        return w.Comparison.model_validate(result).model_dump(mode='json')
