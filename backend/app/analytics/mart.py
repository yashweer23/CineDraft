"""Local SQLite workbench. No production credentials, external packages or telemetry in the dashboard."""
from datetime import datetime,timezone
from pathlib import Path
import re,sqlite3
from .schemas import Stream
from app.domain import Slot

SQL=Path(__file__).with_name('sql'); EPOCH=datetime(1970,1,1,tzinfo=timezone.utc)
def micros(d):
    if d.tzinfo is None:raise ValueError('Supply a timezone-aware instant.')
    v=d-EPOCH;return (v.days*86400+v.seconds)*1000000+v.microseconds

def open_mart(path=':memory:',*,readonly=False):
    if readonly:
        db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        if db.execute('SELECT version FROM meta').fetchone()[0]!='bi-1.0':raise ValueError('Unsupported analytics database.')
        return db
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row;db.executescript((SQL/'schema.sql').read_text());return db

def ingest(db,stream,group,*,observed=False):
    x=Stream.model_validate(stream);sid=x.session_key
    if group not in ('playtest','internal','demo') or (group=='demo')!=(x.origin=='generated_demo') or (group=='playtest' and not observed):raise ValueError('Choose the correct activity group. Human playtests require explicit observation; generated demos stay separate.')
    if x.started>x.captured or x.total!=x.allowance+x.reserve or x.reserve!=35*x.total//100:raise ValueError('Invalid capture window or budget.')
    if not re.fullmatch('[a-f0-9]{64}',sid):raise ValueError('Invalid session key.')
    metadata=(sid,group,micros(x.started),micros(x.captured),x.genre,x.tier,x.catalog,x.rules,x.scoring,x.simulation,int(x.fixture),x.mode,x.total,x.allowance,x.reserve)
    ev={};ops={};starts=[];releases=[];initial={};roster={};abandoned=False;finalized=False;nonces=set();timings={}
    for e in sorted(x.events,key=lambda v:(v.revision,v.kind=='whatif',v.event_key)):
        if e.event_key in ev or not re.fullmatch('[a-f0-9]{64}',e.event_key) or not x.started<=e.at<=x.captured:raise ValueError('Duplicate/invalid event or capture timestamp.')
        if e.kind!='whatif':
            if e.revision in nonces:raise ValueError('Two actions share a revision.')
            nonces.add(e.revision)
            if abandoned or releases:raise ValueError('Action after terminal state.')
        if e.kind in ('start','replay_start'):
            starts.append(e);assert_start=e.revision==0 and e.at==x.started
            if not assert_start:raise ValueError('Start does not match session.')
        if e.kind in ('pick','confirm_recast'):
            if not e.slot or not e.person or e.fee is None or not e.offer:raise ValueError('Selection lacks evidence.')
            if e.kind=='pick':
                if e.slot in initial:raise ValueError('Duplicate initial pick.')
                initial[e.slot]=e.person
            elif e.slot not in initial:raise ValueError('Recast has no prior selection.')
            roster[e.slot]=(e.person,e.fee)
            if len(set(p for p,_ in roster.values()))!=len(roster) or sum(v for _,v in roster.values())>x.allowance:raise ValueError('Unaffordable or duplicate roster.')
        if e.kind=='finalize':
            if set(roster)!=set(Slot):raise ValueError('Incomplete finalized roster.')
            finalized=True
        if e.kind=='abandon':abandoned=True
        if e.kind=='release':
            if not finalized or e.score is None or e.profit is None:raise ValueError('Official outcome requires finalization and score.')
            releases.append(e)
        elif e.profit is not None or e.score is not None:raise ValueError('Only official releases contribute outcomes.')
        if e.kind=='whatif' and not releases:raise ValueError('Comparison precedes official release.')
        ev[e.event_key]=(e.event_key,sid,e.kind,micros(e.at),e.revision,e.slot.value if e.slot else None,e.person,e.offer,e.fee,e.score,e.profit);timings[e.event_key]=e.at
    if len(starts)!=1 or nonces!=set(range(len(nonces))) or len(releases)>1:raise ValueError('Incomplete session evidence.')
    for o in x.opportunities:
        k=(o.offer,o.person)
        if k in ops or o.event_key not in ev or timings[o.event_key]!=o.at:raise ValueError('Invalid or duplicate selectable opportunity.')
        ops[k]=(o.offer,o.person,sid,o.name,o.slot.value,o.kind,micros(o.at),o.event_key)
    for e in x.events:
        if e.kind in ('pick','confirm_recast'):
            op=ops.get((e.offer,e.person))
            if not op or op[4]!=e.slot.value or op[5]!=('pick' if e.kind=='pick' else 'recast') or ev[op[7]][4]>=e.revision:raise ValueError('Selection was not present in its earlier selectable offer.')
    with db:
        existing=db.execute('SELECT * FROM sessions WHERE session_key=?',(sid,)).fetchone();old_events={};old_ops={}
        if existing:
            row=tuple(existing)
            if row[:3]+row[4:]!=metadata[:3]+metadata[4:] or metadata[3]<row[3]:raise ValueError('Conflicting cohort/metadata or stale snapshot; existing data preserved.')
            old_events={v[0]:tuple(v) for v in db.execute('SELECT * FROM events WHERE session_key=?',(sid,))}
            old_ops={(v[0],v[1]):tuple(v) for v in db.execute('SELECT * FROM opportunities WHERE session_key=?',(sid,))}
            if any(ev.get(k)!=v for k,v in old_events.items()) or any(ops.get(k)!=v for k,v in old_ops.items()):raise ValueError('Previously captured evidence changed or disappeared.')
            db.execute('UPDATE sessions SET captured=? WHERE session_key=?',(metadata[3],sid))
        else:db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',metadata)
        db.executemany('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)',[v for k,v in ev.items() if k not in old_events]);db.executemany('INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?)',[v for k,v in ops.items() if k not in old_ops])
    return {'new_sessions':int(not existing),'new_events':len(ev)-len(old_events),'new_opportunities':len(ops)-len(old_ops)}

def report(db,*,group,as_of,start=None,until=None,genre=None,tier=None,catalog=None,rules=None,scoring=None,simulation=None,fixture=None,mode=None):
    if group not in ('playtest','internal','demo'):raise ValueError('Choose one cohort.')
    if start and until and start>=until:raise ValueError('Start must precede exclusive end.')
    for name in ('final_roster','progress','o','e'):db.execute('DROP VIEW IF EXISTS temp.'+name)
    for name in ('cohort','cut'):db.execute('DROP TABLE IF EXISTS temp.'+name)
    args=[group,micros(as_of)];where=['cohort=?','started<=?'];filters={'cohort':group,'as_of':as_of.isoformat()}
    for key,val,op in [('started',start,'>='),('started',until,'<'),('genre',genre,'='),('tier',tier,'='),('catalog',catalog,'='),('rules',rules,'='),('scoring',scoring,'='),('simulation',simulation,'='),('fixture',fixture,'='),('mode',mode,'=')]:
        if val is not None:
            where.append(key+op+'?');args.append(micros(val) if key=='started' else val);filters['from' if op=='>=' else 'until' if op=='<' else key]=val.isoformat() if isinstance(val,datetime) else val
    db.execute('CREATE TEMP TABLE cohort AS SELECT * FROM sessions WHERE '+' AND '.join(where),args);db.execute('CREATE TEMP TABLE cut(as_of INTEGER)');db.execute('INSERT INTO cut VALUES(?)',(micros(as_of),));db.executescript((SQL/'views.sql').read_text())
    result={'version':'bi-1.0','filters':filters}
    for chunk in (SQL/'metrics.sql').read_text().split('-- query: ')[1:]:
        name,sql=chunk.split('\n',1);result[name]=[dict(row) for row in db.execute(sql)]
    return result
