import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import models as m
from app.demo.catalog import DATASET
from app.demo.service import seed,build
from app.drafting.catalog import availability
from app.drafting import auth,service
from app.contracts import CreateDraftRequest
from uuid import uuid4
from test_persistence import database
pytestmark=pytest.mark.integration


def test_demo_build_is_idempotent_and_activation_is_explicit(database):
    c,_=database;first=build(c)
    assert first['dataset']['created'] and first['catalog']['created'] and not first['catalog']['activated']
    with Session(c) as s:assert s.scalar(select(func.count()).select_from(m.CatalogActivation))==0
    second=build(c,activate=True);third=build(c,activate=True)
    assert not second['dataset']['created'] and second['catalog']['activated']
    assert not third['catalog']['activated']
    with Session(c) as s:
        assert s.scalar(select(func.count()).select_from(m.CatalogActivation))==1
        assert s.scalar(select(func.count()).select_from(m.PersonSnapshot).where(m.PersonSnapshot.dataset_id==DATASET))==36
        assert s.scalar(select(func.count()).select_from(m.Credit).where(m.Credit.dataset_id==DATASET))==228
    assert availability(c)['synthetic']
    token=auth.create_session(c)['access_token']
    draft=service.create(c,token,CreateDraftRequest(request_id=uuid4(),genre_id='thriller',tier='blockbuster'))
    assert draft['versions']['dataset_id']==DATASET and len(draft['current_offer']['candidates'])==3


def test_demo_refuses_existing_incomplete_dataset(database):
    c,_=database
    with Session(c) as s,s.begin():
        s.add(m.DatasetVersion(id=DATASET,configuration={},content_hash='0'*64,scope_version='other',role_mapping_version='other',provenance={'source':'fixture'}))
    with Session(c) as s,s.begin(),pytest.raises(ValueError,match='incomplete'):seed(s)
    with Session(c) as s:assert not s.get(m.DatasetVersion,DATASET).sealed
