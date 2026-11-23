"""Synthetic provider-shaped responses. Numeric IDs are test values, never claimed as real TMDB records.
Database integration imports these under source='fixture' and fixture: source keys.
"""
from copy import deepcopy
CONFIG={"images":{"secure_base_url":"https://image.tmdb.org/t/p/","poster_sizes":["w342","original"],"profile_sizes":["w185","original"]}}
MOVIE={"id":900001,"title":"Synthetic Narrative Film","original_language":"en","release_date":"2020-01-01","runtime":100,"status":"Released","adult":False,"video":False,
       "genres":[{"id":18,"name":"Drama"}],"vote_average":7.2,"vote_count":10,"popularity":1.2,"poster_path":None,
       "keywords":{"keywords":[]},"credits":{"cast":[{"id":910001,"name":"Fixture Actor","credit_id":"fixture-cast-1","character":"Detective","order":0,"profile_path":None,"popularity":None}],
       "crew":[{"id":910002,"name":"Fixture Multi Role","credit_id":"fixture-director-1","department":"Directing","job":"Director"},
               {"id":910002,"name":"Fixture Multi Role","credit_id":"fixture-writer-1","department":"Writing","job":"Screenplay"}]}}

def movie(**changes):
    return deepcopy(MOVIE)|changes

class SyntheticClient:
    def __init__(self,fail_once=False):
        self.calls=[];self.fail_once=fail_once
    def configuration(self):
        self.calls.append("configuration");return deepcopy(CONFIG)
    def discover(self,page,cutoff):
        self.calls.append("discovery");return {"page":page,"total_pages":1,"results":[{"id":900001}]}
    def movie(self,movie_id):
        from app.tmdb.client import TMDBError
        self.calls.append(movie_id)
        if self.fail_once:
            self.fail_once=False
            raise TMDBError("retry_exhausted","synthetic temporary failure")
        return movie(id=movie_id)
