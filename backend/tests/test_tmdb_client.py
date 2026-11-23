import httpx2 as httpx
import pytest
from app.tmdb.client import TMDBClient,TMDBError

TOKEN="synthetic-private-test-token"

def client(handler):
    sleeps=[]
    value=TMDBClient(TOKEN,transport=httpx.MockTransport(handler),sleep=sleeps.append,clock=lambda:10,jitter=lambda:0)
    return value,sleeps

def test_bearer_is_header_only_and_appended_credit_request_is_correct():
    seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(200,json={"id":17})
    c,_=client(handler)
    try: assert c.movie(17)=={"id":17}
    finally:c.close()
    request=seen[0]
    assert str(request.url).startswith("https://api.themoviedb.org/3/movie/17?")
    assert request.headers["authorization"]=="Bearer "+TOKEN
    assert TOKEN not in str(request.url)
    assert request.url.params["append_to_response"]=="credits,keywords"

@pytest.mark.parametrize("status",[401,403,404,302,400])
def test_permanent_error_does_not_retry_or_expose_body(status):
    requests=[]
    def handler(request):
        requests.append(request);return httpx.Response(status,text=TOKEN)
    c,_=client(handler)
    with pytest.raises(TMDBError) as error:c.configuration()
    c.close()
    assert TOKEN not in str(error.value) and len(requests)==1

def test_429_retry_after_and_transient_server_failure_recover():
    responses=[httpx.Response(429,headers={"Retry-After":"2"}),httpx.Response(503),httpx.Response(200,json={"ok":True})]
    c,sleeps=client(lambda _:responses.pop(0))
    assert c.configuration()=={"ok":True}
    c.close()
    assert 2 in sleeps and not responses

def test_long_retry_after_stops_for_later_resume():
    c,_=client(lambda _:httpx.Response(429,headers={"Retry-After":"120"}))
    with pytest.raises(TMDBError,match="Resume") as e:c.configuration()
    c.close();assert e.value.code=="rate_limited"

def test_network_errors_are_bounded_and_sanitized():
    count=[]
    def handler(_):
        count.append(1);raise httpx.ReadTimeout(TOKEN)
    c,_=client(handler)
    with pytest.raises(TMDBError) as e:c.configuration()
    c.close();assert len(count)==4 and TOKEN not in str(e.value)

@pytest.mark.parametrize("body",[b"<html>bad gateway</html>",b"[]",b'{"x":NaN}'])
def test_invalid_response_fails_without_logging_body(body):
    c,_=client(lambda _:httpx.Response(200,content=body))
    with pytest.raises(TMDBError):c.configuration()
    c.close()

def test_client_cannot_send_credentials_to_arbitrary_urls():
    c,_=client(lambda _:httpx.Response(200,json={}))
    with pytest.raises(ValueError):c.get("https://unrelated.example/private")
    with pytest.raises(ValueError):c.movie(True)
    c.close()

@pytest.mark.parametrize("token",[""," spaced ","line\nbreak"])
def test_missing_or_malformed_token_is_actionable(token):
    with pytest.raises(TMDBError,match="backend/.env"):TMDBClient(token)


def test_discovery_has_explicit_language_cutoff_and_page():
    requests=[]
    def handler(request):
        requests.append(request);return httpx.Response(200,json={"page":2,"results":[],"total_pages":2})
    c,_=client(handler)
    assert c.discover(2,"2026-01-01")["page"]==2
    c.close()
    params=requests[0].url.params
    assert params["with_original_language"]=="en"
    assert params["primary_release_date.lte"]=="2026-01-01"
    assert params["page"]=="2" and params["include_adult"]=="false"
