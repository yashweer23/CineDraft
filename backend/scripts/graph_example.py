"""Database-free synthetic example: role separation, duplicate jobs and bonus cap."""
import json
from uuid import NAMESPACE_URL, uuid5
from app.talent.calculation import Film, Person, Credit
from app.collaboration.calculation import build_graph, edge_key, NO_SHARED


def uid(name):
    return str(uuid5(NAMESPACE_URL, 'cinedraft:synthetic:graph-example:' + name))


def example():
    films=[Film(uid(f'film-{i}'),'fixture',f'fixture:graph-example-{i}',f'Synthetic shared film {i}') for i in range(1,7)]
    people=[Person(uid(name)) for name in ('director-writer','actor','composer')]
    credits=[]
    for film in films:
        credits += [Credit(people[0].id,film.id,'director','Director'),Credit(people[1].id,film.id,'actor','Actor')]
    credits += [Credit(people[0].id,films[0].id,'writer','Story'),Credit(people[0].id,films[0].id,'writer','Screenplay'),
        Credit(people[2].id,films[-1].id,'composer','Original Music Composer')]
    graph=build_graph(films,people,credits)
    lookup={edge['edge_id']:edge for edge in graph['edges']}
    strong=lookup[edge_key((people[0].id,'director'),(people[1].id,'actor'))]
    separate=lookup[edge_key((people[0].id,'writer'),(people[1].id,'actor'))]
    missing=edge_key((people[0].id,'writer'),(people[2].id,'composer')) not in lookup
    return {'synthetic':True,'tmdb_requests':0,'database_required':False,
        'demonstration':{'director_actor':{'films':strong['shared_movie_count'],'bonus':strong['bonus']},
            'writer_actor':{'films':separate['shared_movie_count'],'bonus':separate['bonus']},
            'writer_composer':{'films':0,'bonus':0,'message':NO_SHARED if missing else 'Unexpected evidence'}},
        'people':[{'person_id':p.id,'label':name} for p,name in zip(people,('Synthetic Director / Writer','Synthetic Actor','Synthetic Composer'))],
        'films':[{'movie_id':f.id,'title':f.title} for f in films], 'graph':graph}

if __name__=='__main__':
    print(json.dumps(example(),indent=2,ensure_ascii=False,allow_nan=False))
