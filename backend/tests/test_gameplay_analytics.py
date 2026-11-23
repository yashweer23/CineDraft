from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import json,sqlite3
import pytest
from app.analytics.demo import streams
from app.analytics.mart import open_mart,ingest,report
from app.analytics.dashboard import render
from scripts.gameplay_analytics import main,instant

END=instant('2026-11-01')
@pytest.fixture
def db():
    c=open_mart()
    for s in streams():ingest(c,s,'demo')
    yield c;c.close()

def sample(c,**kw):return report(c,group='demo',as_of=END,**kw)

def test_completion_funnel_reconciles_evidence_and_distinguishes_still_open(db):
    r=sample(db);o=r['overview'][0]
    assert (o['started'],o['completed'],o['abandoned'],o['unfinished'])==(12,7,3,2)
    assert [v['reached'] for v in r['funnel']]==[12,11,11,8,8,7,7,7,7,7,7]
    assert len({v['start_event'] for v in r['trace']})==12 and len({v['release_event'] for v in r['trace'] if v['release_event']})==7
    for v in r['trace']:
        if v['release_event']:assert db.execute('SELECT kind,session_key FROM events WHERE event_key=?',(v['release_event'],)).fetchone()[:]==('release',v['session_key'])
    assert o['replay_starts']==2 and o['comparisons']==1 and o['confirmed_recasts']==2

def test_denominators_use_selectable_offers_and_final_rosters(db):
    r=sample(db);director=[v for v in r['talent'] if v['slot']=='director'];assert sum(v['selectable_offers'] for v in director)==26 # initial offer in 12 films + one reroll, two candidates each
    assert sum(v['selections'] for v in director)==11
    recast=next(v for v in director if v['name'].endswith(' C'));assert recast['pick_pct'] is None and recast['official_films']==2
    assert sum(v['official_films'] for v in director)==7
    b=r['budget'][0];assert b['committed_talent']==7860000==sum(v['total_fees'] for v in r['allocations'])
    assert b['unused_allowance']+b['committed_talent']+b['reserved_production']==b['total_budget']
    assert b['utilization_pct']==6.4

def test_median_uses_even_middle_pair_and_preserves_idle_time(db):
    r=sample(db);co=next(x for x in r['rounds'] if x['slot']=='co_lead');assert co['measured_picks']==8 and co['median_seconds']==88.5
    s=next(streams());s.events[2].at=s.events[1].at-timedelta(seconds=1)
    for op in s.opportunities:
        if op.event_key==s.events[2].event_key:op.at=s.events[2].at
    empty=open_mart();ingest(empty,s,'demo');row=next(x for x in sample(empty)['rounds'] if x['slot']=='lead');assert row['clock_reversals']==1 and row['measured_picks']==0 and row['median_seconds'] is None;empty.close()

def test_repeat_ingestion_adds_no_sessions_opportunities_or_events(db):
    before=sample(db)
    for s in streams():assert ingest(db,s,'demo')=={'new_sessions':0,'new_events':0,'new_opportunities':0}
    assert sample(db)==before

def test_partial_then_complete_extends_stable_history():
    db=open_mart();s=next(streams());early=s.model_copy(deep=True);early.events=early.events[:3];keys={e.event_key for e in early.events};early.opportunities=[o for o in early.opportunities if o.event_key in keys];early.captured=early.events[-1].at
    ingest(db,early,'demo');assert sample(db)['funnel'][2]['reached']==1
    out=ingest(db,s,'demo');assert out['new_sessions']==0 and out['new_events']>0 and sample(db)['overview'][0]['completed']==1
    with pytest.raises(ValueError,match='stale'):ingest(db,early,'demo')
    db.close()

def test_capture_collision_preserves_existing_records(db):
    s=next(streams());s.opportunities[0].name='Conflicting issued card';before=sample(db)
    with pytest.raises(ValueError,match='changed or disappeared'):ingest(db,s,'demo')
    assert sample(db)==before

@pytest.mark.parametrize('group,observed',[('playtest',False),('playtest',True),('internal',False)])
def test_generated_activity_cannot_enter_human_or_test_cohorts(db,group,observed):
    with pytest.raises(ValueError):ingest(db,next(streams()),group,observed=observed)

def test_operator_attestation_and_separate_catalog_source():
    s=next(streams());s.origin='owner_export';db=open_mart()
    with pytest.raises(ValueError):ingest(db,s,'playtest')
    ingest(db,s,'playtest',observed=True);assert report(db,group='playtest',as_of=END)['overview'][0]['fixture_sessions']==1
    with pytest.raises(ValueError):ingest(db,s,'internal')
    assert report(db,group='internal',as_of=END)['overview'][0]['started']==0;db.close()

def test_half_open_start_window_asof_and_filter_intersection(db):
    r=sample(db,start=instant('2026-10-01'),until=instant('2026-10-03'));assert r['overview'][0]['started']==2
    r=sample(db,genre='drama',tier='studio',rules='classic-1.0');assert r['overview'][0]['started']==2
    initial=list(streams())[0];r=report(db,group='demo',as_of=initial.started);assert r['overview'][0]['started']==1 and r['overview'][0]['completed']==0 and r['funnel'][1]['reached']==0
    r=sample(db,catalog="x' OR 1=1 --");assert r['overview'][0]['started']==0 and r['budget'][0]['utilization_pct'] is None
    assert 'No drafts started' in render(r)

@pytest.mark.parametrize('kind',['repeated_event','extra_outcome','missing_offer','wrong_slot','missing_revision','over_budget'])
def test_damaged_evidence_rejected_atomically(kind):
    db=open_mart();s=next(streams());pick=next(e for e in s.events if e.kind=='pick')
    if kind=='repeated_event':s.events.append(deepcopy(pick))
    if kind=='extra_outcome':s.events[-1].score=100
    if kind=='missing_offer':s.opportunities=[o for o in s.opportunities if (o.offer,o.person)!=(pick.offer,pick.person)]
    if kind=='wrong_slot':s.opportunities[0].slot=s.events[2].slot
    if kind=='missing_revision':s.events.pop(1)
    if kind=='over_budget':pick.fee=s.allowance+1
    with pytest.raises(ValueError):ingest(db,s,'demo')
    assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0;db.close()

def test_offline_html_escapes_untrusted_catalog_names(db):
    with db:db.execute("UPDATE opportunities SET name='<img src=x onerror=alert(1)>'")
    html=render(sample(db));assert '&lt;img' in html and '<img src=x' not in html and '<script' not in html

def test_cli_demo_then_readonly_filtered_report(tmp_path):
    out=tmp_path/'demo';assert main(['demo','--out',str(out)])==0
    data=out/'gameplay.sqlite';before=data.read_bytes();out2=tmp_path/'report'
    assert main(['report','--db',str(data),'--cohort','demo','--genre','thriller','--out',str(out2)])==0
    assert json.loads((out2/'metrics.json').read_text())['overview'][0]['started']==6
    assert data.read_bytes()==before
