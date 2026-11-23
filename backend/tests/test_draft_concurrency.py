"""Independent committed schema: exercise real row locks from separate connections."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID,uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,text,select,func
from sqlalchemy.orm import Session
from app import contracts as w,models as m
from app.drafting import auth,service
from app.drafting.errors import DraftProblem
from test_draft_integration import seed,pick_body
pytestmark=pytest.mark.integration

@pytest.fixture
def committed_game():
    url=os.environ.get('TEST_DATABASE_URL')
    if not url:pytest.skip('Real PostgreSQL required: run python -m scripts.run_integration')
    admin=create_engine(url,hide_parameters=True);assert admin.dialect.name=='postgresql'
    schema='phase7_concurrency_'+uuid4().hex
    # The generated schema is the only schema this fixture creates/drops.
    with admin.begin() as c:c.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine=create_engine(url,hide_parameters=True,connect_args={'options':f'-c search_path={schema} -c statement_timeout=10000'},pool_size=3,max_overflow=0)
    try:
        with engine.begin() as c:
            config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
            config.set_main_option('script_location',str(Path(__file__).resolve().parents[1]/'migrations'))
            config.attributes['connection']=c;command.upgrade(config,'head')
        seed(engine);t=auth.create_session(engine)['access_token']
        d=service.create(engine,t,w.CreateDraftRequest(request_id=uuid4(),genre_id='drama',tier='blockbuster'))
        yield engine,t,d
    finally:
        engine.dispose()
        with admin.begin() as c:c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()

@pytest.mark.parametrize('same_request',[True,False])
def test_simultaneous_picks_serialize_without_double_spending(committed_game,same_request):
    engine,t,d=committed_game;first=pick_body(d)
    second=first if same_request else first.model_copy(update={'request_id':uuid4()})
    barrier=Barrier(2)
    def submit(body):
        barrier.wait(timeout=10)
        try:return service.mutate(engine,t,UUID(d['draft_id']),'pick',body)
        except DraftProblem as error:return error.code
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(submit,b) for b in (first,second)]
        results=[f.result(timeout=20) for f in futures]
    if same_request:assert results[0]==results[1] and isinstance(results[0],dict)
    else:assert sum(isinstance(r,dict) for r in results)==1 and 'stale_revision' in results
    current=service.read(engine,t,UUID(d['draft_id']))
    assert current['revision']==1 and len(current['picks'])==1
    assert current['budget']['talent_spend_usd']==current['picks'][0]['locked_fee_usd']
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(m.ActionRecord))==1
        assert s.scalar(select(func.count()).select_from(m.Offer))==2


def test_simultaneous_create_reuses_one_saved_creation_response(committed_game):
    engine,t,d=committed_game;body=w.CreateDraftRequest(request_id=uuid4(),genre_id='drama',tier='blockbuster');barrier=Barrier(2)
    def submit():
        barrier.wait(timeout=10);return service.create(engine,t,body)
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(submit) for _ in range(2)]
        results=[f.result(timeout=20) for f in futures]
    assert results[0]==results[1]
    assert len(service.list_drafts(engine,t)['items'])==2
