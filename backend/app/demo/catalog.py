"""A versioned fictional catalog for a complete local demonstration."""
from datetime import date
from decimal import Decimal
from uuid import NAMESPACE_URL,uuid5
from app.domain import GENRES,Role,Slot,TIERS
from app.repository import canonical_hash
from app.talent.calculation import Film,Person,Credit,build_features,build_prices
from app.collaboration.calculation import build_graph
from app.drafting.assignment import Talent,minimum_assignment

VERSION='portfolio-demo-1.0'
DATASET='fixture:portfolio-v1'
LABEL='portfolio-v1'
JOBS={'director':'Director','actor':'Actor','writer':'Screenplay','cinematographer':'Director of Photography','composer':'Original Music Composer'}

def identity(key):return str(uuid5(NAMESPACE_URL,'cinedraft:'+VERSION+':'+key))

def records():
    """JSON-compatible observations; no clock, network, names of real people or RNG."""
    films=[];people=[];credits=[];genres=list(GENRES)
    for i in range(20):
        films.append(dict(id=identity(f'film:{i}'),key=f'fixture:portfolio-v1:film:{i}',
            title=f'Synthetic {GENRES[genres[i//2]]} Study {i+1:02}',date=f'{2001+i:04}-06-15',
            rating=str(Decimal('5.0')+Decimal(i%8)/2),votes=300+i*271,popularity=str(5+i*3),
            genres=sorted({genres[i//2],genres[(i+3)%10]})))
    for role in Role:
        for i in range(12 if role==Role.ACTOR else 6):
            key=f'{role.value}:{i}';pid=identity('person:'+key)
            people.append(dict(id=pid,key='fixture:portfolio-v1:person:'+key,
                name=f'Synthetic {role.value.title()} {i+1:02}',popularity=None if i==0 else str(i*11)))
            professional_roles=[role.value]
            if role==Role.DIRECTOR and i==0:professional_roles.append('writer')
            if role==Role.WRITER and i==0:professional_roles.append('composer')
            cohort=i%6;works=sorted({cohort,cohort+6,cohort+12,(cohort+1)%20,(cohort+7)%20,(cohort+13)%20})
            for professional_role in professional_roles:
                for film in works:
                    credits.append(dict(person_id=pid,movie_id=films[film]['id'],role=professional_role,job=JOBS[professional_role]))
    return dict(films=films,people=people,credits=sorted(credits,key=lambda c:(c['person_id'],c['role'],c['movie_id'])))

def observations(data=None):
    data=data or records()
    films=[Film(id=f['id'],source='fixture',source_key=f['key'],title=f['title'],release_date=date.fromisoformat(f['date']),
        rating=Decimal(f['rating']),votes=f['votes'],popularity=Decimal(f['popularity']),genres=frozenset(f['genres'])) for f in data['films']]
    people=[Person(p['id'],Decimal(p['popularity']) if p['popularity'] is not None else None) for p in data['people']]
    credits=[Credit(**c) for c in data['credits']]
    return films,people,credits

def manifest(data=None):
    data=data or records()
    return dict(schema_version=VERSION,synthetic=True,source='fixture',purpose='Opt-in local portfolio demonstration',
        input_rows_hash=canonical_hash(data),people=len(data['people']),movies=len(data['films']),credits=len(data['credits']),
        person_roles=len({(c['person_id'],c['role']) for c in data['credits']}))

def preview():
    data=records();films,people,credits=observations(data)
    features=build_features(films,people,credits);prices=build_prices(features['profiles']);graph=build_graph(films,people,credits)
    pool=[Talent(row['person_id'],row['role'],row['fee_usd']) for row in prices['rows']]
    assignment=minimum_assignment(pool,list(Slot));cost=assignment['cost_usd'] if assignment else None
    return dict(synthetic=True,mode='offline preview; no database writes',dataset_id=DATASET,manifest=manifest(data),
        input_hash=features['input_hash'],feature_hash=canonical_hash(features['profiles']),pricing_hash=canonical_hash(prices['rows']),
        graph_hash=graph['output_hash'],graph_nodes=len(graph['nodes']),graph_edges=len(graph['edges']),
        minimum_assignment=assignment,tiers={tier:dict(talent_budget_usd=total*65//100,enabled=cost is not None and cost<=total*65//100) for tier,total in TIERS.items()},
        scope='Fictional people, films, ratings and credits. Production feature/pricing/graph algorithms; no saved drafts or results.')
