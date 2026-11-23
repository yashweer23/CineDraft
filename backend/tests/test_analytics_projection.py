from types import SimpleNamespace as N
from uuid import uuid4
from datetime import datetime,timedelta,timezone
from app.analytics.service import project,key
from app.analytics.mart import open_mart,ingest,report

def test_project_real_receipt_shapes_excludes_blocked_cards_and_private_fields():
    t=datetime(2026,10,1,tzinfo=timezone.utc);pid=str(uuid4());oid=str(uuid4());did=uuid4();id1=uuid4()
    d=N(id=did,created_at=t,revision=1,genre_id='drama',tier='indie',rules_id='classic-1.0',scoring_id='baseline-1.0',simulation_version='simulation-1.0',total_budget_usd=10000000,talent_budget_usd=6500000,reserve_usd=3500000)
    offer={'kind':'pick','slot':'director','offer_id':oid,'candidates':[{'selectable':True,'card':{'person_id':pid,'name':'Practice Director','private_key':'SECRET_CANARY'}},{'selectable':False,'card':{'person_id':str(uuid4()),'name':'BLOCKED_CANARY'}}]}
    act=N(id=id1,command='pick',revision_after=1,created_at=t+timedelta(seconds=30),request_body={'person_id':pid,'offer_id':oid,'request_id':'SECRET_CANARY'},response_body={'picks':[{'person_id':pid,'offer_id':oid,'slot':'director','locked_fee_usd':350000}],'current_offer':None,'seed':'SECRET_CANARY'})
    rt=N(creation_response={'current_offer':offer,'owner_key':'SECRET_CANARY'});c=N(id='draft-catalog:sample',configuration={'source':'fixture'});end=t+timedelta(minutes=2)
    x=project(d,rt,c,[act],None,[],False,False,end);assert x.origin=='owner_export' and len(x.opportunities)==1 and len(x.events)==2
    assert x.events[1].event_key==key('action',id1) and x.events[1].fee==350000
    assert all(v not in x.model_dump_json() for v in ['SECRET_CANARY','BLOCKED_CANARY',str(did),str(id1),oid])
    with open_mart() as db:
        ingest(db,x,'internal');r=report(db,group='internal',as_of=end);assert r['rounds'][0]['median_seconds']==30 and r['talent'][0]['pick_pct']==100
