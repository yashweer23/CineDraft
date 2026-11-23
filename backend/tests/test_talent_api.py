from pathlib import Path
import json
from fastapi.testclient import TestClient
from app.main import create_app
from app.catalog import session_for
from test_foundation import settings,FakeDatabase

def test_live_talent_routes_remain_read_only_alongside_releases():
    with TestClient(create_app(settings(),FakeDatabase())) as c:
        spec=c.get('/api/openapi.json').json()
        for route in ['/api/talent/versions','/api/talent/{pricing_id}/profiles','/api/talent/{pricing_id}/profiles/{person_id}/{role}','/api/talent/{pricing_id}/report']:
            assert set(spec['paths'][route])=={'get'}
        assert '/api/v1/drafts/{draft_id}/release' in spec['paths']
        assert spec['components']['schemas']['TalentProfile']['properties']['fee_is_fictional']['const'] is True
        assert spec['components']['schemas']['TalentProfile']['properties']['notable_works']['maxItems']==5
        assert spec==json.loads((Path(__file__).resolve().parents[2]/'contracts/openapi.current.json').read_text())

def test_talent_request_validation_keeps_errors_structured():
    app=create_app(settings(),FakeDatabase())
    app.dependency_overrides[session_for]=lambda:None
    with TestClient(app) as c:
        for path in ['/api/talent/pricing:test/profiles?role=producer','/api/talent/pricing:test/profiles?role=actor&genre=unknown','/api/talent/pricing:test/profiles?role=actor&limit=100','/api/talent/pricing:test/profiles/not-a-uuid/director']:
            response=c.get(path)
            assert response.status_code==422,response.text
            assert response.json()['error']['code']=='validation_error'
