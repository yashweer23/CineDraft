from fastapi.testclient import TestClient
from app.main import create_app
from app.catalog import session_for
from test_foundation import settings, FakeDatabase


def test_graph_openapi_has_read_only_evidence_routes():
    with TestClient(create_app(settings(),FakeDatabase())) as c:
        spec=c.get('/api/openapi.json').json()
        paths=[p for p in spec['paths'] if p.startswith('/api/collaboration')]
        assert len(paths)==6
        assert all(set(spec['paths'][p])=={'get'} for p in paths)
        assert spec['components']['schemas']['GraphVersion']['properties']['playable']['const'] is False
        assert '/api/v1/drafts/{draft_id}/release' in spec['paths']


def test_graph_request_validation_happens_before_database_reads():
    app=create_app(settings(),FakeDatabase());app.dependency_overrides[session_for]=lambda:None
    with TestClient(app) as c:
        for suffix in ['/nodes?role=producer','/edges?person_id=bad','/edges?limit=51',
                       '/nodes?offset=-1','/edges/bad/films','/pair?person_a=bad']:
            response=c.get('/api/collaboration/graph:test'+suffix)
            assert response.status_code==422,response.text
            assert response.json()['error']['code']=='validation_error'
