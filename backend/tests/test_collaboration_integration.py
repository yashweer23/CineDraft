"""Real PostgreSQL only; synthetic data, full migration and service/API invariants."""
from copy import deepcopy
import pytest
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from alembic import command
from app import models as m
from app.fixtures import seed_fixture, DATASET, DRAFT_ID, fixture_id
from app.repository import canonical_hash
from app.collaboration.service import build, BuildProblem
from app.main import create_app
from app.catalog import session_for
from test_foundation import settings, FakeDatabase
from test_persistence import database
pytestmark=pytest.mark.integration


def seed(c):
    with Session(c) as s,s.begin(): seed_fixture(s)


def client_for(c):
    app=create_app(settings(),FakeDatabase())
    def db():
        with Session(c) as s: yield s
    app.dependency_overrides[session_for]=db
    return TestClient(app)


def test_graph_publication_rerun_and_history_preservation(database):
    c=database[0];seed(c)
    first=build(c,DATASET,'first');second=build(c,DATASET,'first');build(c,DATASET,'second')
    assert first['created'] and not second['created']
    assert first['graph_hash']==second['graph_hash']
    assert first['report']['nodes']==9 and first['report']['edges']==35
    with Session(c) as s:
        assert s.get(m.GraphVersion,'graph:first').sealed
        assert s.scalar(select(func.count()).select_from(m.GraphEvidence).where(m.GraphEvidence.graph_id=='graph:first'))==35
        assert s.get(m.Result,DRAFT_ID) is not None
        assert s.get(m.PricingVersion,'fixture:pricing-v1').sealed


def test_preview_missing_dataset_and_label_conflict(database):
    c=database[0];seed(c)
    preview=build(c,DATASET,'preview',dry_run=True)
    assert preview['dry_run'] and not preview['created']
    with Session(c) as s,s.begin():
        assert s.get(m.GraphVersion,'graph:preview') is None
        s.add(m.GraphVersion(id='graph:partial',dataset_id=DATASET,algorithm_version='test',configuration={},content_hash='0'*64))
    with pytest.raises(BuildProblem,match='incomplete'): build(c,DATASET,'partial')
    with pytest.raises(BuildProblem,match='sealed'): build(c,'missing','missing')


def test_failed_evidence_insert_rolls_back_entire_new_graph(database):
    c=database[0];seed(c);build(c,DATASET,'old')
    c.execute(text("CREATE FUNCTION fail_graph_evidence() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure' USING ERRCODE='23514'; END $$"))
    c.execute(text('CREATE TRIGGER fail_evidence BEFORE INSERT ON graph_evidence FOR EACH ROW EXECUTE FUNCTION fail_graph_evidence()'))
    with pytest.raises(IntegrityError): build(c,DATASET,'failed')
    with Session(c) as s:
        assert s.get(m.GraphVersion,'graph:failed') is None
        assert s.scalar(select(func.count()).select_from(m.GraphNode).where(m.GraphNode.graph_id=='graph:failed'))==0
        assert s.get(m.GraphVersion,'graph:old').sealed


@pytest.mark.parametrize('sql',[
 "UPDATE graph_versions SET sealed=false", "DELETE FROM graph_versions",
 "UPDATE graph_nodes SET film_count=2", "DELETE FROM graph_nodes",
 "UPDATE graph_edges SET bonus=8", "DELETE FROM graph_edges",
 "UPDATE graph_evidence SET jobs_a='[]'::jsonb", "DELETE FROM graph_evidence",
])
def test_published_graph_members_are_immutable(database,sql):
    c=database[0];seed(c);build(c,DATASET,'immutable')
    with Session(c) as s:
        with pytest.raises(IntegrityError),s.begin_nested(): s.execute(text(sql))
        assert s.get(m.GraphVersion,'graph:immutable').sealed


def unsealed_copy(s):
    old=s.get(m.GraphVersion,'graph:base')
    copy=m.GraphVersion(id='graph:unsealed',dataset_id=DATASET,algorithm_version=old.algorithm_version,
        configuration=deepcopy(old.configuration),content_hash=old.content_hash)
    s.add(copy);s.flush()
    for n in s.scalars(select(m.GraphNode).where(m.GraphNode.graph_id==old.id)).all():
        s.add(m.GraphNode(graph_id=copy.id,dataset_id=DATASET,person_id=n.person_id,role=n.role,film_count=n.film_count))
    s.flush()
    return copy


def test_self_edges_wrong_jobs_and_incomplete_seal_rejected(database):
    c=database[0];seed(c);build(c,DATASET,'base')
    with Session(c) as s,s.begin():
        version=unsealed_copy(s)
        original=s.scalars(select(m.GraphEdge).where(m.GraphEdge.graph_id=='graph:base')).first()
        fields={key:getattr(original,key) for key in ('edge_id','person_a','role_a','person_b','role_b','shared_movie_count','bonus')}
        with pytest.raises(IntegrityError),s.begin_nested():
            s.add(m.GraphEdge(graph_id=version.id,**(fields|{'person_b':original.person_a,'role_b':original.role_a})));s.flush()
        s.add(m.GraphEdge(graph_id=version.id,**fields));s.flush()
        evidence=s.scalars(select(m.GraphEvidence).where(m.GraphEvidence.graph_id=='graph:base',m.GraphEvidence.edge_id==original.edge_id)).first()
        with pytest.raises(IntegrityError),s.begin_nested():
            s.add(m.GraphEvidence(graph_id=version.id,dataset_id=DATASET,edge_id=original.edge_id,movie_id=evidence.movie_id,jobs_a=['Invented job'],jobs_b=evidence.jobs_b));s.flush()
        with pytest.raises(IntegrityError),s.begin_nested():
            version.sealed=True;s.flush()


def test_graph_api_pins_roles_films_pagination_and_reversed_pair(database):
    c=database[0];seed(c);build(c,DATASET,'api')
    base='/api/collaboration/graph:api'
    with client_for(c) as client:
        assert client.get('/api/collaboration/versions').json()['items'][0]['graph_id']=='graph:api'
        assert client.get(base+'/nodes?limit=2').json()['next_offset']==2
        assert client.get(base+'/nodes?q=Director&role=director').json()['items'][0]['name']=='Fixture Director'
        edge_page=client.get(base+'/edges?limit=1')
        assert edge_page.status_code==200,edge_page.text
        edge=edge_page.json()['items'][0];a=edge['a'];b=edge['b']
        params={'person_a':a['person_id'],'role_a':a['role'],'person_b':b['person_id'],'role_b':b['role']}
        first=client.get(base+'/pair',params=params).json()
        reverse=client.get(base+'/pair',params={'person_a':b['person_id'],'role_a':b['role'],'person_b':a['person_id'],'role_b':a['role']}).json()
        assert first==reverse and first['edge']['bonus']==4
        detail=client.get(base+'/edges/'+edge['edge_id']+'/films?limit=1')
        assert detail.status_code==200,detail.text
        film=detail.json()['items'][0]
        assert film['source']=='fixture' and film['source_url'] is None
        assert film['jobs_a'] and film['jobs_b'] and detail.json()['next_offset'] is None
        assert client.get(base+'/report').json()['parameters']['edge_bonus_cap']==12
        assert client.get(base+'/pair',params=params|{'person_b':a['person_id']}).status_code==422
        assert client.get('/api/collaboration/graph:missing/edges').status_code==404
        # Same endpoint must satisfy person AND role filters.
        for item in client.get(base+'/edges',params={'person_id':a['person_id'],'role':a['role']}).json()['items']:
            assert any(n['person_id']==a['person_id'] and n['role']==a['role'] for n in (item['a'],item['b']))


def test_valid_roles_without_shared_movie_return_zero_not_missing_person(database):
    c=database[0];seed(c)
    dataset='fixture:isolated-graph'
    config={'synthetic':True,'purpose':'isolated graph nodes'}
    with Session(c) as s,s.begin():
        ds=m.DatasetVersion(id=dataset,scope_version='fixture:scope',role_mapping_version='fixture:roles',configuration=config,content_hash=canonical_hash(config),provenance={'source':'fixture'})
        s.add(ds);s.flush()
        for name,role,job in [('director','director','Director'),('lead','actor','Actor')]:
            pid=fixture_id('person-'+name);mid=fixture_id('graph-film-'+name)
            s.add(m.Movie(id=mid,source='fixture',source_key='fixture:graph-film-'+name));s.flush()
            s.add(m.MovieSnapshot(dataset_id=dataset,movie_id=mid,title='Synthetic isolated '+name,runtime_minutes=90,eligibility='eligible',eligibility_reason='Synthetic',provenance={'source':'fixture'}))
            s.add(m.PersonSnapshot(dataset_id=dataset,person_id=pid,name='Synthetic '+name,coverage={'synthetic':True}));s.flush()
            s.add(m.Credit(dataset_id=dataset,person_id=pid,movie_id=mid,dedupe_key='fixture:'+name,kind='cast' if role=='actor' else 'crew',role=role,job=job,provenance={'source':'fixture'}));s.flush()
        ds.sealed=True
    result=build(c,dataset,'isolated');assert result['report']['isolated_nodes']==2
    with client_for(c) as client:
        params={'person_a':str(fixture_id('person-director')),'role_a':'director','person_b':str(fixture_id('person-lead')),'role_b':'actor'}
        response=client.get('/api/collaboration/graph:isolated/pair',params=params)
        assert response.status_code==200,response.text
        assert response.json()['message']=='No shared credits found in this dataset.'
        assert response.json()['edge']['edge_id'] is None and response.json()['edge']['bonus']==0
        assert client.get('/api/collaboration/graph:isolated/pair',params=params|{'role_a':'composer'}).status_code==404


def test_phase6_downgrade_preserves_phase5_data_then_upgrades(database):
    c,config=database;seed(c);build(c,DATASET,'migration')
    command.downgrade(config,'0002_phase4')
    assert c.scalar(text('SELECT count(*) FROM results'))==1
    assert c.scalar(text("SELECT version_num FROM alembic_version"))=='0002_phase4'
    command.upgrade(config,'head')
    assert c.scalar(text('SELECT count(*) FROM graph_versions'))==0
