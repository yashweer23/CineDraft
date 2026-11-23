import json
import pytest
import httpx2 as httpx
from app.schemas import ReadyHealth
from app.validation.http_benchmark import Route,local_origin,request,measure,routes
from app.validation.metrics import percentile

@pytest.mark.parametrize('value',['https://example.com','http://127.0.0.1','http://127.0.0.1:8001/path','http://u:p@localhost:8001','http://localhost:8001/?token=x','http://localhost:8001/#x','http://localhost:bad','http://127.0.0.2:8001'])
def test_benchmark_only_accepts_explicit_local_origins(value):
    with pytest.raises(ValueError):local_origin(value)

@pytest.mark.parametrize('value',['http://127.0.0.1:8001','http://localhost:8001/','http://[::1]:8001'])
def test_loopback_origins(value):assert local_origin(value)==value.rstrip('/')


def test_nearest_rank_and_empty_percentiles():
    assert percentile([5,1,4,3,2],.5)==3
    assert percentile([5,1,4,3,2],.95)==5
    assert percentile([],.5) is None


def test_load_mix_and_errors_are_recorded_without_tokens_or_bodies():
    seen=[];token='private-test-token';private=Route('owner','/private',ReadyHealth,True)
    def handler(req):
        seen.append(req)
        if req.url.path=='/bad':return httpx.Response(503,json={'secret':'not in report'})
        return httpx.Response(200,json={'status':'ready','database':'connected'},headers={'cache-control':'no-store'})
    with httpx.Client(base_url='http://localhost:8001',transport=httpx.MockTransport(handler)) as client:
        result=measure(client,[private,Route('failing','/bad',ReadyHealth)],token,12,3,0)
    assert result['requests']==12 and result['errors']==6 and result['error_rate']==.5
    assert result['endpoints']['owner']['requests']==6 and result['endpoints']['failing']['latency_success_ms']['p50'] is None
    assert all(r.headers.get('authorization')==('Bearer '+token if r.url.path=='/private' else None) for r in seen)
    assert token not in json.dumps(result) and 'not in report' not in json.dumps(result)

@pytest.mark.parametrize('kind,expected',[('redirect','http_302'),('json','invalid_response'),('schema','invalid_response'),('cache','missing_no_store'),('timeout','timeout')])
def test_failures_are_errors_not_fast_successes(kind,expected):
    def handler(req):
        if kind=='timeout':raise httpx.ReadTimeout('secret url',request=req)
        if kind=='redirect':return httpx.Response(302,headers={'location':'https://example.com'})
        if kind=='json':return httpx.Response(200,text='not JSON')
        if kind=='schema':return httpx.Response(200,json={'status':'no'})
        return httpx.Response(200,json={'status':'ready','database':'connected'})
    with httpx.Client(base_url='http://localhost:8001',transport=httpx.MockTransport(handler),follow_redirects=False) as c:
        assert request(c,Route('test','/',ReadyHealth,True),'token')['error']==expected
        with pytest.raises(ValueError,match='Warmup'):measure(c,[Route('test','/',ReadyHealth,True)],'token',4,2,1)


def test_route_mix_is_fixed_and_dataset_is_escaped():
    values=routes('fixture:x/y');assert len(values)==4
    assert 'x%2Fy' in values[2].path
    assert not any(r.private for r in values)
