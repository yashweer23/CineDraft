"""Opt-in publication. Each stage commits atomically; a failed build can resume."""
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from app import models as m
from app.domain import GENRES
from app.repository import canonical_hash
from app.demo.catalog import records,manifest,DATASET,LABEL,VERSION
from app.talent.service import build as build_talent
from app.collaboration.service import build as build_graph
from app.drafting.catalog import prepare


def seed(session):
    if not session.scalar(text('SELECT pg_try_advisory_xact_lock(41014,1)')):raise ValueError('Another portfolio dataset build is active; retry after it finishes.')
    data=records();config=manifest(data);digest=canonical_hash(config)
    existing=session.get(m.DatasetVersion,DATASET)
    if existing:
        if not (existing.sealed and existing.configuration==config and existing.content_hash==digest
                and existing.scope_version==VERSION and existing.role_mapping_version=='fixture:portfolio-roles-v1'):
            raise ValueError('Portfolio dataset differs or is incomplete. Existing history was preserved.')
        return dict(dataset_id=DATASET,created=False,**config)
    for key,name in GENRES.items():
        if session.get(m.Genre,key) is None:session.add(m.Genre(id=key,name=name))
    dataset=m.DatasetVersion(id=DATASET,configuration=config,content_hash=digest,scope_version=VERSION,
        role_mapping_version='fixture:portfolio-roles-v1',provenance={'source':'fixture','synthetic':True,'upstream_requests':0})
    session.add(dataset);session.flush()
    def ensure(model,row):
        existing=session.get(model,UUID(row['id']))
        if existing is not None:
            if (existing.source,existing.source_key)!=('fixture',row['key']):raise ValueError('Fictional identity conflicts with existing source history.')
        else:session.add(model(id=UUID(row['id']),source='fixture',source_key=row['key']));session.flush()
    for film in data['films']:
        ensure(m.Movie,film)
        session.add(m.MovieSnapshot(dataset_id=DATASET,movie_id=UUID(film['id']),title=film['title'],original_language='en',
            release_date=date.fromisoformat(film['date']),runtime_minutes=95,poster_path=None,audience_rating=Decimal(film['rating']),
            vote_count=film['votes'],popularity=Decimal(film['popularity']),eligibility='eligible',
            eligibility_reason='Fictional local demonstration',provenance={'source':'fixture','synthetic':True}))
        session.flush()
        for genre in film['genres']:session.add(m.MovieGenre(dataset_id=DATASET,movie_id=UUID(film['id']),genre_id=genre))
    for person in data['people']:
        ensure(m.Person,person)
        session.add(m.PersonSnapshot(dataset_id=DATASET,person_id=UUID(person['id']),name=person['name'],profile_path=None,
            popularity=Decimal(person['popularity']) if person['popularity'] is not None else None,coverage={'synthetic':True,'scope':'portfolio-demo-1.0'}))
    session.flush()
    for credit in data['credits']:
        session.add(m.Credit(dataset_id=DATASET,person_id=UUID(credit['person_id']),movie_id=UUID(credit['movie_id']),
            dedupe_key=canonical_hash(credit),kind='cast' if credit['role']=='actor' else 'crew',role=credit['role'],job=credit['job'],
            department='Acting' if credit['role']=='actor' else credit['role'].title(),provenance={'source':'fixture','synthetic':True}))
    session.flush();dataset.sealed=True;session.flush()
    return dict(dataset_id=DATASET,created=True,**config)


def build(engine,*,activate=False):
    with Session(engine) as session,session.begin():dataset=seed(session)
    talent=build_talent(engine,DATASET,LABEL)
    graph=build_graph(engine,DATASET,LABEL)
    catalog=prepare(engine,talent['pricing_id'],graph['graph_id'],LABEL,activate=activate)
    return dict(synthetic=True,dataset=dataset,talent=talent,graph=graph,catalog=catalog,
        activation_requested=activate,scope='No prior catalog, draft, account or result was rewritten. Activation affects future practice drafts only.')
