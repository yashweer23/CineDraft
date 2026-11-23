"""Bounded, read-only load test of a local API plus real PostgreSQL inventory."""
import argparse,getpass,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
import httpx2 as httpx
from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.config import Settings
from app.database import Database
from app.schemas import ReadyHealth
from app.drafting.schemas import CatalogAvailability
from app.validation.metrics import machine
from app.validation.http_benchmark import local_origin,routes,measure,inventory

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=local_origin,default='http://127.0.0.1:8001')
    p.add_argument('--requests',type=int,default=240);p.add_argument('--concurrency',type=int,default=4)
    p.add_argument('--warmup',type=int,default=2);p.add_argument('--timeout',type=float,default=10)
    p.add_argument('--draft',type=UUID,help='Your released practice film; adds four owner routes and prompts privately for its token.')
    p.add_argument('--server-description',required=True,help='API/DB hardware, containers, worker count and reload setting; no secrets.')
    p.add_argument('--out',type=Path,default=Path('../validation-output/api.json'))
    a=p.parse_args(argv)
    if not 1<=a.concurrency<=16 or not a.concurrency<=a.requests<=10000 or not 1<=a.warmup<=20 or not .1<=a.timeout<=60:
        p.error('Use concurrency 1..16, requests concurrency..10000, warmup 1..20, timeout .1..60')
    db=None
    try:
        token=(os.environ.get('CINEDRAFT_BENCHMARK_TOKEN') or getpass.getpass('Recovery or account token (hidden): ')) if a.draft else None
        if a.draft and (not token or '\n' in token or '\r' in token):raise ValueError('Missing or invalid owner token')
        with httpx.Client(base_url=a.base,follow_redirects=False,trust_env=False,timeout=a.timeout,
                          limits=httpx.Limits(max_connections=a.concurrency,max_keepalive_connections=a.concurrency)) as client:
            health=client.get('/api/health/ready');health.raise_for_status();ReadyHealth.model_validate(health.json())
            response=client.get('/api/v1/catalog');response.raise_for_status();catalog=CatalogAvailability.model_validate(response.json())
            db=Database(Settings())
            with Session(db.engine) as session,session.begin():
                session.execute(text('SET TRANSACTION READ ONLY'));dataset=inventory(session,catalog)
            result=measure(client,routes(catalog.dataset_id,a.draft),token,a.requests,a.concurrency,a.warmup)
        report=dict(schema_version='phase13-http-benchmark-v1',executed_at=datetime.now(timezone.utc).isoformat(),
            mode='live HTTP with separate PostgreSQL inventory',client_machine=machine(),server_description=a.server_description,
            dataset=dataset,profile='owner-read' if a.draft else 'public-read',timeout_seconds=a.timeout,
            method='Persistent connections; closed-loop workers, deterministic equal round-robin route mix; no retries or redirects. Request timing includes body decoding and schema validation. Nearest-rank p50/p95. Warmup excluded. HTTP target and DB inventory must refer to the same local stack.',
            limits='Read endpoints only; no write throughput, stress-limit or production capacity claim. Client and server may contend for CPU. Reports omit tokens, draft IDs and response bodies.',
            **result)
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('profile','requests','errors','error_rate','requests_per_second','latency_success_ms')},indent=2))
        return 1 if result['errors'] else 0
    except (httpx.HTTPError,SQLAlchemyError,ValidationError,SettingsError,ValueError,EOFError):
        print('Benchmark stopped: check the local API, backend/.env database, active catalog, and owner access to a released practice film. No new measurement report was written; an older report may still exist.',file=sys.stderr);return 1
    finally:
        if db:db.close()
if __name__=='__main__':raise SystemExit(main())
