"""Read-only raw catalog. No TMDB calls or fictional game attributes on requests."""
from collections import defaultdict
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app import models as m
from app.catalog_schemas import DatasetPage, MoviePage, PersonPage, FilmographyPage
from app.domain import Role
from app.schemas import ErrorEnvelope
from app.tmdb.payloads import image_url

NOTICE = "This product uses the TMDB API but is not endorsed or certified by TMDB."
router=APIRouter(prefix="/api/catalog",tags=["Raw catalog"],responses={404:{"model":ErrorEnvelope},503:{"model":ErrorEnvelope},422:{"model":ErrorEnvelope}})
Limit=Annotated[int,Query(ge=1,le=50)]
Offset=Annotated[int,Query(ge=0,le=100000)]

def session_for(request:Request):
    try:
        with Session(request.app.state.database.engine) as session:
            yield session
    except SQLAlchemyError:
        raise HTTPException(503,"Catalog database unavailable or migration missing.") from None

DB=Annotated[Session,Depends(session_for)]

def dataset(session,dataset_id):
    row=session.get(m.DatasetVersion,dataset_id)
    if row is None or not row.sealed:raise HTTPException(404,"Published dataset not found.")
    return row

def picture(ds,path,kind):
    config=ds.configuration.get("images")
    return image_url(config,path,kind) if config else None

def movie_view(ds,snapshot,identity):
    return dict(movie_id=identity.id,source=identity.source,source_key=identity.source_key,title=snapshot.title,
                release_date=snapshot.release_date,runtime_minutes=snapshot.runtime_minutes,
                audience_rating=float(snapshot.audience_rating) if snapshot.audience_rating is not None else None,
                vote_count=snapshot.vote_count,poster_url=picture(ds,snapshot.poster_path,"poster"),
                eligibility=snapshot.eligibility,eligibility_reason=snapshot.eligibility_reason)

@router.get("/attribution")
def attribution():
    return {"source":"TMDB","notice":NOTICE,"url":"https://www.themoviedb.org","branding":"https://www.themoviedb.org/about/logos-attribution"}

@router.get("/datasets",response_model=DatasetPage)
def datasets(session:DB,limit:Limit=20,offset:Offset=0):
    rows=session.scalars(select(m.DatasetVersion).where(m.DatasetVersion.sealed.is_(True)).order_by(m.DatasetVersion.id).offset(offset).limit(limit+1)).all()
    return {"items":[dict(id=d.id,source=d.provenance.get("source","unknown"),created_at=d.created_at,
                          scope_version=d.scope_version,role_mapping_version=d.role_mapping_version,report=d.configuration.get("report",{})) for d in rows[:limit]],
            "next_offset":offset+limit if len(rows)>limit else None}

@router.get("/{dataset_id}/movies",response_model=MoviePage)
def movies(dataset_id:str,session:DB,limit:Limit=20,offset:Offset=0,eligibility:Literal["eligible","excluded","review","all"]="eligible"):
    ds=dataset(session,dataset_id)
    q=select(m.MovieSnapshot,m.Movie).join(m.Movie,m.Movie.id==m.MovieSnapshot.movie_id).where(m.MovieSnapshot.dataset_id==ds.id)
    if eligibility!="all":q=q.where(m.MovieSnapshot.eligibility==eligibility)
    rows=session.execute(q.order_by(m.Movie.id).offset(offset).limit(limit+1)).all()
    return {"dataset_id":ds.id,"items":[movie_view(ds,s,movie) for s,movie in rows[:limit]],"next_offset":offset+limit if len(rows)>limit else None}

@router.get("/{dataset_id}/people",response_model=PersonPage)
def people(dataset_id:str,session:DB,limit:Limit=20,offset:Offset=0,role:Role|None=None):
    ds=dataset(session,dataset_id)
    credit_query=select(m.Credit.id).join(m.MovieSnapshot,(m.MovieSnapshot.dataset_id==m.Credit.dataset_id)&(m.MovieSnapshot.movie_id==m.Credit.movie_id)).where(m.Credit.dataset_id==ds.id,m.Credit.person_id==m.Person.id,m.MovieSnapshot.eligibility=="eligible",m.Credit.role.is_not(None))
    if role is not None:credit_query=credit_query.where(m.Credit.role==role.value)
    q=select(m.PersonSnapshot,m.Person).join(m.Person,m.Person.id==m.PersonSnapshot.person_id).where(m.PersonSnapshot.dataset_id==ds.id,credit_query.exists())
    rows=session.execute(q.order_by(m.Person.id).offset(offset).limit(limit+1)).all()
    return {"dataset_id":ds.id,"items":[dict(person_id=i.id,source=i.source,source_key=i.source_key,name=s.name,
            profile_url=picture(ds,s.profile_path,"profile"),coverage=s.coverage) for s,i in rows[:limit]],"next_offset":offset+limit if len(rows)>limit else None}

@router.get("/{dataset_id}/people/{person_id}/films",response_model=FilmographyPage)
def filmography(dataset_id:str,person_id:UUID,role:Role,session:DB,limit:Limit=20,offset:Offset=0):
    ds=dataset(session,dataset_id)
    if session.get(m.PersonSnapshot,(ds.id,person_id)) is None:raise HTTPException(404,"Person not found in dataset.")
    linked=select(m.Credit.movie_id).where(m.Credit.dataset_id==ds.id,m.Credit.person_id==person_id,m.Credit.role==role.value)
    rows=session.execute(select(m.MovieSnapshot,m.Movie).join(m.Movie,m.Movie.id==m.MovieSnapshot.movie_id).where(m.MovieSnapshot.dataset_id==ds.id,m.MovieSnapshot.eligibility=="eligible",m.MovieSnapshot.movie_id.in_(linked)).order_by(m.MovieSnapshot.release_date.desc().nullslast(),m.Movie.id).offset(offset).limit(limit+1)).all()
    jobs=defaultdict(set)
    if rows:
        for movie_id,job in session.execute(select(m.Credit.movie_id,m.Credit.job).where(m.Credit.dataset_id==ds.id,m.Credit.person_id==person_id,m.Credit.role==role.value,m.Credit.movie_id.in_([i.id for _,i in rows[:limit]]))):jobs[movie_id].add(job)
    return {"dataset_id":ds.id,"person_id":person_id,"role":role.value,
            "items":[movie_view(ds,s,i)|{"credited_jobs":sorted(jobs[i.id])} for s,i in rows[:limit]],"next_offset":offset+limit if len(rows)>limit else None}
