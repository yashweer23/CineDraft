"""Twelve invented sessions for a reproducible SQL exercise. No real user observations."""
from datetime import datetime,timedelta,timezone
from uuid import uuid5,NAMESPACE_URL
from app.domain import Slot
from .schemas import Stream
from .service import key

def streams():
    slots=[s.value for s in Slot];base=datetime(2026,10,1,12,tzinfo=timezone.utc)
    def person(slot,i):return str(uuid5(NAMESPACE_URL,f'cinedraft-demo:{slot}:{i}'))
    for film,depth in enumerate([8]*7+[2,2,2,4,0]):
        sid=key('demo-session',film);start=base+timedelta(days=film);time=start;events=[];opps=[];rev=0;counter=0
        def add(kind,delay=0,**fields):
            nonlocal rev,time,counter
            time+=timedelta(seconds=delay);event=dict(event_key=key('demo-event',f'{film}:{counter}'),kind=kind,at=time,revision=rev,**fields);events.append(event);counter+=1
            if kind!='whatif':rev+=1
            return event
        def issue(slot,e,kind='pick',options=(0,1)):
            oid=key('demo-offer',f'{film}:{e["event_key"]}:{slot}');
            for i in options:opps.append(dict(kind=kind,offer=oid,person=person(slot,i),name=f'Sample {slot.replace("_"," ").title()} {chr(65+i)}',slot=slot,at=e['at'],event_key=e['event_key']))
            return oid
        e=add('replay_start' if film in (5,6) else 'start');o=issue(slots[0],e)
        for i,slot in enumerate(slots[:depth]):
            if film==1 and i==0:o=issue(slot,add('reroll',3),'pick',(0,1))
            selected=(film+i)%2;e=add('pick',85+film if i==2 else 12+film+i,slot=slot,person=person(slot,selected),offer=o,fee=100000+10000*i+5000*selected)
            if i<7:o=issue(slots[i+1],e)
        if depth==8:
            if film in (0,4):
                o=issue(slots[0],add('preview_recast',15),'recast',(2,));add('confirm_recast',20,slot=slots[0],person=person(slots[0],2),offer=o,fee=180000)
            add('finalize',20)
            if film==2:add('release_failed',3)
            add('release',5,score=60+3*film,profit=(film-2)*125000)
            if film==0:add('whatif',30)
        elif film in (7,8,9):add('abandon',10)
        tier,total=('studio',50000000) if film%3==0 else ('indie',10000000)
        yield Stream(origin='generated_demo',session_key=sid,started=start,captured=time+timedelta(minutes=1),genre='drama' if film%2==0 else 'thriller',tier=tier,catalog='demo:practice-v1',rules='classic-1.0',scoring='baseline-1.0',simulation='simulation-1.0',fixture=True,mode='practice',total=total,allowance=total*65//100,reserve=total*35//100,events=events,opportunities=opps)
