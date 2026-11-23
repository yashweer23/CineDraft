"""Run a clearly synthetic calibration example without PostgreSQL or an API token."""
import json
from datetime import date
from decimal import Decimal as D
from uuid import NAMESPACE_URL, uuid5
from app.talent.calculation import Film, Person, Credit, build_features, build_prices

def uid(label): return str(uuid5(NAMESPACE_URL, 'cinedraft:fixture:phase5:'+label))

def example():
    observations = [('Supported Drama', '8.0', 5000, '10', ['drama']),
        ('Two-Vote Outlier', '9.9', 2, '5', ['drama','mystery']),
        ('Unrated Story', None, 0, None, ['drama']),
        ('Older Comedy', '6.0', 1000, '20', ['comedy']),
        ('Adventure Film', '7.0', 3000, '15', ['adventure']),
        ('Crime Film', '7.5', 2000, '12', ['crime']),
        ('Romance Film', '6.5', 500, '8', ['romance'])]
    films=[Film(uid(name),'fixture','fixture:'+str(i),'Synthetic '+name,
        date(2010+i,1,1),D(rating) if rating else None,votes,D(pop) if pop else None,
        None,'en',frozenset(genres)) for i,(name,rating,votes,pop,genres) in enumerate(observations)]
    people=[Person(uid('visible-actor'),D(500)),Person(uid('less-visible-actor'),D(5)),Person(uid('director-writer'),None)]
    credits=[Credit(p.id,f.id,'actor','Actor') for p in people[:2] for f in films]
    credits += [Credit(people[2].id,f.id,'director','Director') for f in films[:3]]
    credits += [Credit(people[2].id,films[0].id,'writer',job) for job in ['Writer','Screenplay']]
    result=build_features(films,people,credits);prices=build_prices(result['profiles'])
    names={people[0].id:'Synthetic Visible Actor',people[1].id:'Synthetic Less-Visible Actor',people[2].id:'Synthetic Director-Writer'}
    return {'synthetic':True,'tmdb_requests':0,'note':'Invented demonstration records. These are not real films, people, fees or source ratings.',
        'people':names,'movies':{f.id:f.title for f in films},'features':result,'pricing':prices}

if __name__=='__main__':print(json.dumps(example(),indent=2,ensure_ascii=False,allow_nan=False))
