"""Read-only HTTP measurements. Never serializes payloads, URLs with IDs, or tokens."""
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlsplit, quote
import httpx2 as httpx
from pydantic import ValidationError
from sqlalchemy import select,func,text
from app import models as m
from app.schemas import ReadyHealth
from app.catalog_schemas import PersonPage,MoviePage
from app.drafting.schemas import CatalogAvailability,LiveDraft,RosterView
from app.simulation.schemas import SavedResult
from app.analytics.schemas import Stream
from app.validation.metrics import percentile

@dataclass(frozen=True)
class Route:
    label: str
    path: str
    schema: type
    private: bool=False

def local_origin(value):
    try:
        u=urlsplit(value);port=u.port
        valid=(u.scheme=='http' and u.hostname in ('127.0.0.1','localhost','::1') and
            u.username is None and u.password is None and not u.query and not u.fragment and u.path in ('','/') and port is not None and port>0)
    except ValueError: valid=False
    if not valid: raise ValueError('Use an HTTP loopback origin with an explicit port and no credentials/path/query.')
    return value.rstrip('/')

def routes(dataset,draft_id=None):
    ds=quote(dataset,safe='')
    result=[Route('readiness','/api/health/ready',ReadyHealth),Route('catalog','/api/v1/catalog',CatalogAvailability),
        Route('people','/api/catalog/'+ds+'/people?limit=20',PersonPage),
        Route('movies','/api/catalog/'+ds+'/movies?limit=20',MoviePage)]
    if draft_id is not None:
        base='/api/v1/drafts/'+str(draft_id)
        result += [Route('draft',base,LiveDraft,True),Route('roster',base+'/roster',RosterView,True),
                   Route('result',base+'/result',SavedResult,True),Route('analytics',base+'/analytics-events',Stream,True)]
    return result

def request(client,route,token=None):
    started=time.perf_counter();status=None;error=None
    try:
        response=client.get(route.path,headers={'Authorization':'Bearer '+token} if route.private and token else {})
        status=response.status_code
        if status!=200:error=f'http_{status}'
        else:
            route.schema.model_validate(response.json())
            if route.private and 'no-store' not in response.headers.get('cache-control',''):error='missing_no_store'
    except httpx.TimeoutException:error='timeout'
    except httpx.HTTPError:error='transport'
    except (ValidationError,ValueError):error='invalid_response'
    return dict(route=route.label,status=status,error=error,latency_ms=(time.perf_counter()-started)*1000)

def measure(client,route_list,token,requests,concurrency,warmup):
    if not route_list or not 1<=concurrency<=16 or not concurrency<=requests<=10000 or not 0<=warmup<=20:
        raise ValueError('Invalid benchmark bounds')
    # Warm every route, exclude warmup and fail fast on authentication/schema errors.
    for route in route_list:
        for _ in range(warmup):
            if request(client,route,token)['error']:raise ValueError('Warmup failed; verify catalog, owner, completed practice film and API health.')
    started=time.perf_counter()
    def worker(index):
        return [request(client,route_list[i%len(route_list)],token) for i in range(index,requests,concurrency)]
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        rows=[r for batch in executor.map(worker,range(concurrency)) for r in batch]
    elapsed=time.perf_counter()-started
    def summarize(values):
        success=[r['latency_ms'] for r in values if r['error'] is None];all_values=[r['latency_ms'] for r in values]
        return dict(requests=len(values),errors=sum(r['error'] is not None for r in values),
            status_counts=dict(Counter(str(r['status']) for r in values)),error_counts=dict(Counter(r['error'] for r in values if r['error'])),
            latency_all_ms={'p50':percentile(all_values,.50),'p95':percentile(all_values,.95)},
            latency_success_ms={'p50':percentile(success,.50),'p95':percentile(success,.95)})
    total=summarize(rows)
    return dict(**total,concurrency=concurrency,warmup_per_route=warmup,elapsed_seconds=elapsed,
        requests_per_second=len(rows)/elapsed,error_rate=total['errors']/len(rows),
        endpoints={r.label:summarize([v for v in rows if v['route']==r.label]) for r in route_list})

def inventory(session,catalog):
    """Caller opens a READ ONLY transaction. Also usable in isolated PG fixtures."""
    if session.get_bind().dialect.name!='postgresql':raise ValueError('Real PostgreSQL required')
    stored=session.get(m.DraftCatalog,catalog.catalog_id)
    if stored is None or not stored.sealed or (stored.dataset_id,stored.pricing_id,stored.graph_id)!=(catalog.dataset_id,catalog.pricing_id,catalog.graph_id):
        raise ValueError('API catalog and configured PostgreSQL inventory do not match')
    return dict(postgresql_version=session.scalar(text('SHOW server_version')),
        migration=session.scalar(text('SELECT version_num FROM alembic_version')),
        catalog_id=stored.id,catalog_hash=stored.content_hash,dataset_id=stored.dataset_id,synthetic=catalog.synthetic,
        people=session.scalar(select(func.count()).select_from(m.PersonSnapshot).where(m.PersonSnapshot.dataset_id==stored.dataset_id)),
        movies=session.scalar(select(func.count()).select_from(m.MovieSnapshot).where(m.MovieSnapshot.dataset_id==stored.dataset_id)),
        person_roles=session.scalar(select(func.count()).select_from(m.RolePrice).where(m.RolePrice.pricing_id==stored.pricing_id)),
        draft_count=session.scalar(select(func.count()).select_from(m.Draft)))
