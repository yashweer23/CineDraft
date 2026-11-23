"""Pure simulation-1.0. No database, clock, network, or process-global randomness."""
from decimal import Decimal,localcontext,ROUND_HALF_UP,ROUND_FLOOR
from uuid import NAMESPACE_URL,uuid5
from app.domain import Slot,SLOT_ROLES
from app.repository import canonical_hash
from app.drafting.schemas import FrozenDraft
from app.drafting.rules import RULES,SCORING,RULES_ID,SCORING_ID,SIMULATION_VERSION,RELATIONSHIPS
from app.talent.calculation import FEATURE_VERSION
from app.collaboration.calculation import canonical_pair,edge_key,NO_SHARED

D=Decimal
PRECISION=64
RANDOM_VERSION='sha256-uniform53-1.0'
MANIFEST={
    'simulation_version':SIMULATION_VERSION,'scoring_id':SCORING_ID,'scoring_hash':canonical_hash(SCORING),
    'arithmetic':'decimal','precision':PRECISION,'rounding':'ROUND_HALF_UP',
    'random_version':RANDOM_VERSION,'seed_derivation':'canonical JSON [random_version, frozen_seed, stream, draw_index]; SHA-256',
    'sample_mapping':'first 64 hash bits shifted right by 11; n / 2^53; low + (high-low)*u',
    'interval':'[low, high); 2^53 equally spaced values','streams':['critics','audience','revenue'],'draw_index':0,
    'iterations':1,'review_display_decimals':2,'weekly_rounding':'floor weeks 1-3; residual to week 4',
}
MANIFEST_HASH=canonical_hash(MANIFEST)

class SimulationInputError(ValueError):pass


def dec(value,*,low=None,high=None):
    if type(value) not in (int,float,str,Decimal):raise SimulationInputError('Expected a finite numeric input.')
    try:number=D(str(value))
    except Exception:raise SimulationInputError('Expected a finite numeric input.') from None
    if not number.is_finite() or (low is not None and number<low) or (high is not None and number>high):
        raise SimulationInputError('Numeric input is outside the supported range.')
    return number


def exact(value):
    """No binary float conversion in arithmetic or precision-bearing output."""
    return format(value,'f') if isinstance(value,D) else str(value)


def clamp(value,low=0,high=100):return max(D(low),min(D(high),value))
def dollars(value):return int(value.quantize(D(1),rounding=ROUND_HALF_UP))
def display(value):return float(value.quantize(D('0.01'),rounding=ROUND_HALF_UP))


def draw(seed,stream,index=0):
    if not seed or stream not in ('critics','audience','revenue') or type(index) is not int or index<0:
        raise SimulationInputError('Unsupported random stream or draw index.')
    low,high=(D('-.6'),D('.6')) if stream=='revenue' else (D(-5),D(5))
    digest=canonical_hash([RANDOM_VERSION,seed,stream,index]);integer=int(digest[:16],16)>>11
    with localcontext() as ctx:
        ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_UP
        unit=D(integer)/D(2**53);noise=low+(high-low)*unit
        return {'stream':stream,'draw_index':index,'sha256':digest,'sample_uint53':str(integer),
                'unit_interval':exact(unit),'noise':exact(noise)}


def score_components(genre,talent,chemistry,spend,envelope):
    with localcontext() as ctx:
        ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_UP
        g=dec(genre,low=0,high=100);t=dec(talent,low=0,high=100);h=dec(chemistry,low=60,high=100)
        if type(spend) is not int or type(envelope) is not int or not 0<=spend<=envelope or envelope<=0:
            raise SimulationInputError('Invalid talent allocation.')
        efficiency=clamp((g+t)/2*(1-D('.30')*D(spend)/D(envelope)))
        components=[]
        for name,value in [('genre',g),('talent',t),('chemistry',h),('efficiency',efficiency)]:
            weight=D(SCORING['studio_weights'][name]);contribution=value*weight
            components.append(dict(name=name,value=exact(value),weight=exact(weight),contribution=exact(contribution)))
        raw=sum((D(c['contribution']) for c in components),D(0))
        return components,raw,dollars(raw)


def release_math(genre,talent,chemistry,appeal,production,noise):
    """Bounded noises can be supplied by independent arithmetic tests, never HTTP clients."""
    with localcontext() as ctx:
        ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_UP
        g=dec(genre,low=0,high=100);t=dec(talent,low=0,high=100);h=dec(chemistry,low=60,high=100);p=dec(appeal,low=0,high=100)
        if type(production) is not int or production<=0:raise SimulationInputError('Invalid production commitment.')
        if set(noise)!={'critics','audience','revenue'}:raise SimulationInputError('Three named noise streams are required.')
        nc=dec(noise['critics'],low=-5,high=5);na=dec(noise['audience'],low=-5,high=5);nr=dec(noise['revenue'],low=D('-.6'),high=D('.6'))
        critics=clamp(D('.50')*t+D('.35')*g+D('.15')*h+nc)
        audience=clamp(D('.30')*t+D('.30')*g+D('.20')*h+D('.20')*p+na)
        multiplier=clamp(D('.50')+D('.018')*audience+D('.010')*critics+D('.008')*p+nr,D('.2'),5)
        gross=dollars(D(production)*multiplier);marketing=dollars(D(production)*D('.20'))
        receipts=dollars(D(gross)*D('.50'));total=production+marketing;profit=receipts-total
        retention=clamp(D('.40')+D('.004')*audience,D('.40'),D('.80'))
        weights=[retention**i for i in range(4)];denominator=sum(weights)
        weeks=[int((D(gross)*w/denominator).to_integral_value(rounding=ROUND_FLOOR)) for w in weights[:3]]
        weeks.append(gross-sum(weeks))
        return dict(critics=display(critics),audience=display(audience),critics_unrounded=exact(critics),audience_unrounded=exact(audience),
            gross_multiplier=exact(multiplier),production_cost_usd=production,marketing_usd=marketing,total_cost_usd=total,
            worldwide_gross_usd=gross,studio_receipts_usd=receipts,profit_usd=profit,
            return_on_total_cost_percent=exact(D(100)*D(profit)/D(total)),weekly_retention=exact(retention),weekly_gross_usd=weeks)


def verify_snapshot(frozen,input_hash):
    if not isinstance(frozen,FrozenDraft):raise SimulationInputError('Only finalized phase7-v1 inputs can be released by this engine.')
    if canonical_hash(frozen.model_dump(mode='json'))!=input_hash:raise SimulationInputError('Frozen input hash does not match.')
    v=frozen.draft.versions
    if (v.rules_id!=RULES_ID or v.scoring_id!=SCORING_ID or v.simulation_version!=SIMULATION_VERSION or
        frozen.rules_configuration!=RULES or frozen.scoring_configuration!=SCORING):
        raise SimulationInputError('Unsupported frozen rules or scoring version. Existing inputs were preserved.')
    if canonical_hash(frozen.graph_configuration)!=v.graph_hash:raise SimulationInputError('Frozen graph manifest hash does not match.')


def team_inputs(frozen):
    """Validate selected profiles and exactly the designated evidence relationships."""
    profiles={(p.person_id,p.role):p for p in frozen.role_features};cards={c.person_id:c for c in frozen.cards}
    roster={p.slot.value:p for p in frozen.draft.picks};rows=[];warnings=[]
    weights=list(map(D,SCORING['slot_weights']));denominator=sum(weights)
    for i,slot in enumerate(Slot):
        pick=roster[slot.value];role=SLOT_ROLES[slot];profile=profiles[(pick.person_id,role)];card=cards[pick.person_id];a=profile.attributes
        if a.get('schema_version')!=FEATURE_VERSION:raise SimulationInputError('Unsupported frozen role-feature version.')
        try:t=dec(a['talent_strength'],low=0,high=100);g=dec(a['genre_fit'][frozen.draft.genre_id],low=0,high=100)
        except KeyError:raise SimulationInputError('Frozen role features are incomplete.') from None
        if t!=dec(card.talent_strength) or g!=dec(card.genre_fit):raise SimulationInputError('Frozen card and role attributes disagree.')
        observed=a.get('popularity_percentile');p=D(50) if observed is None else dec(observed,low=0,high=100)
        coverage=a.get('coverage',{});gaps=profile.evidence.get('genre_catalog_gaps',[])
        if coverage.get('level')=='low':warnings.append(f'{slot.value}: low source coverage; values are game proxies.')
        if frozen.draft.genre_id in gaps:warnings.append(f'{slot.value}: selected genre has a catalog gap; a prior was used.')
        if role.value=='actor' and observed is None:warnings.append(f'{slot.value}: missing popularity uses neutral cast appeal 50.')
        rows.append(dict(slot=slot.value,person_id=str(pick.person_id),name=card.name,role=role.value,source=card.source,
            hiring_fee_usd=pick.locked_fee_usd,weight=exact(weights[i]),talent=exact(t),genre_fit=exact(g),cast_appeal=exact(p) if role.value=='actor' else None,
            popularity_missing=observed is None,coverage=coverage,genre_contribution=exact(g*weights[i]/denominator),talent_contribution=exact(t*weights[i]/denominator)))
    # Aggregate directly from the weighted numerators (not rounded display contributions).
    g=sum((D(r['genre_fit'])*D(r['weight']) for r in rows),D(0))/denominator
    t=sum((D(r['talent'])*D(r['weight']) for r in rows),D(0))/denominator
    p=sum((D(r['cast_appeal']) for r in rows if r['role']=='actor'),D(0))/4
    if [(e.get('slot_a'),e.get('slot_b')) for e in frozen.collaborations]!=RELATIONSHIPS:
        raise SimulationInputError('Frozen chemistry must contain the twelve designated ordered relationships.')
    edges=[];total_bonus=0
    for e in frozen.collaborations:
        a,b=e['slot_a'],e['slot_b'];pa,pb=roster[a],roster[b]
        left,right=canonical_pair(pa.person_id,SLOT_ROLES[Slot(a)],pb.person_id,SLOT_ROLES[Slot(b)])
        if e.get('canonical_a')!=list(left) or e.get('canonical_b')!=list(right):raise SimulationInputError('Collaboration endpoints do not match the roster.')
        count=e.get('shared_movie_count');evidence=e.get('evidence')
        if type(count) is not int or count<0 or not isinstance(evidence,list) or len(evidence)!=count:
            raise SimulationInputError('Collaboration count and evidence disagree.')
        movie_ids=[item.get('movie_id') for item in evidence]
        if any(not isinstance(mid,str) or not mid for mid in movie_ids) or len(set(movie_ids))!=count:
            raise SimulationInputError('Collaboration evidence must contain distinct movie identities.')
        for item in evidence:
            for key in ('jobs_a','jobs_b'):
                jobs=item.get(key)
                if not isinstance(jobs,list) or not jobs or any(not isinstance(j,str) or not j.strip() for j in jobs):
                    raise SimulationInputError('Collaboration evidence requires exact credited jobs.')
        bonus=min(12,4*count);key=edge_key(left,right) if count else None
        if type(e.get('bonus')) is not int or e['bonus']!=bonus or e.get('edge_id')!=key:
            raise SimulationInputError('Collaboration bonus or identity does not match its evidence.')
        total_bonus+=bonus
        edges.append(dict(slot_a=a,slot_b=b,person_id_a=str(pa.person_id),person_id_b=str(pb.person_id),name_a=cards[pa.person_id].name,name_b=cards[pb.person_id].name,
            role_a=SLOT_ROLES[Slot(a)].value,role_b=SLOT_ROLES[Slot(b)].value,edge_id=key,shared_movie_count=count,bonus=bonus,
            message='Shared credits found in this dataset.' if count else NO_SHARED,evidence=evidence,
            canonical_a=list(left),canonical_b=list(right)))
    h=D(60)+D(40)*D(total_bonus)/D(144)
    return g,t,h,p,rows,edges,warnings


def simulate(frozen,input_hash):
    verify_snapshot(frozen,input_hash)
    with localcontext() as ctx:
        ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_UP
        g,t,h,p,rows,edges,warnings=team_inputs(frozen);budget=frozen.draft.budget
        components,raw,score=score_components(g,t,h,budget.talent_spend_usd,budget.talent_budget_usd)
        draws=[draw(frozen.seed,name) for name in MANIFEST['streams']]
        finance=release_math(g,t,h,p,budget.reserve_usd+budget.talent_spend_usd,{r['stream']:r['noise'] for r in draws})
        top=sorted(enumerate(rows),key=lambda item:(-D(item[1]['genre_contribution']),item[0]))[:2]
        return dict(schema_version='phase8-v1',draft_id=str(frozen.draft.draft_id),input_hash=input_hash,
            simulation_id=str(uuid5(NAMESPACE_URL,'cinedraft:'+SIMULATION_VERSION+':'+input_hash)),simulation_version=SIMULATION_VERSION,
            synthetic=frozen.synthetic,versions=frozen.draft.versions.model_dump(mode='json'),studio_score=score,studio_score_unrounded=exact(raw),
            score_components=components,cast_appeal=exact(p),unused_talent_budget_usd=budget.talent_remaining_usd,**finance,
            reproducibility=dict(manifest=MANIFEST,manifest_hash=MANIFEST_HASH,seed=frozen.seed,draws=draws),
            explanation=dict(note='Fictional game simulation, not a prediction of any real film or person.',
                rows=rows,top_genre_contributors=[row['slot'] for _,row in top],chemistry_edges=edges,warnings=warnings,
                production_reserve_usd=budget.reserve_usd,talent_spend_usd=budget.talent_spend_usd,
                finance_note='Production commitment is reserve plus hires. Marketing is an additional modeled cost. Gross is theatrical revenue; receipts are the studio share.' ))
