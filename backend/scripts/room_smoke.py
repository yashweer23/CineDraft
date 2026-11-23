"""Opt-in live local check. Creates two guests and one synthetic cooperative film."""
import argparse
import json
import secrets
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4
from websockets.sync.client import connect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='http://127.0.0.1:8001')
    parser.add_argument('--origin', default='http://localhost:5174')
    args=parser.parse_args()
    target=urlsplit(args.api)
    if target.scheme!='http' or target.hostname not in ('127.0.0.1','localhost','api') or target.username or target.password or target.query or target.fragment or target.path not in ('','/'):
        parser.error('--api must be a local HTTP origin (localhost, 127.0.0.1, or Docker service api).')
    base=args.api.rstrip('/')
    def http(path, token='', body=None, expected=200):
        data=json.dumps(body).encode() if body is not None else None
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        try:
            with urlopen(Request(base+path,data=data,headers=headers),timeout=20) as response:
                status=response.status;value=json.load(response)
        except HTTPError as error:
            status=error.code;value=json.load(error)
        if status!=expected:
            raise RuntimeError(f'{path}: expected HTTP {expected}, received {status}; code={value.get("error",{}).get("code","unknown")}')
        return value
    catalog=http('/api/v1/catalog')
    if not catalog['synthetic']:
        raise RuntimeError('Activate the fictional portfolio catalog first; this check only uses synthetic data.')
    if not any(t['tier']=='blockbuster' and t['enabled'] for t in catalog['tiers']):
        raise RuntimeError('The synthetic catalog must enable Blockbuster.')
    a,b=[http('/api/v1/sessions',body={},expected=201)['access_token'] for _ in range(2)]
    create={'request_id':str(uuid4()),'invite_code':secrets.token_urlsafe(32),'genre_id':'thriller','tier':'blockbuster','turn_seconds':180}
    room=http('/api/v1/rooms',a,create,201);id=room['room_id'];root='/api/v1/rooms/'+id
    assert http('/api/v1/rooms',a,create,201)==room
    http(root,b,expected=404)
    joined=http(root+'/join',b,{'request_id':str(uuid4()),'invite_code':create['invite_code']})
    room=http(root+'/start',a,{'request_id':str(uuid4()),'expected_revision':joined['revision']})
    # A real socket, separate from HTTP, validates the configured browser origin and first-frame auth.
    uri='ws://'+target.netloc+root+'/live'
    with connect(uri,origin=args.origin,proxy=None,open_timeout=10,close_timeout=3) as ws:
        ws.send(json.dumps({'token':b}))
        event=json.loads(ws.recv(timeout=10))
        assert event['type']=='room' and event['room']['room_id']==id and event['room']['seat']==1
    for turn in range(8):
        owner=(a,b)[turn%2];other=(b,a)[turn%2]
        offer=room['draft']['current_offer']
        card=next(v for v in offer['candidates'] if v['selectable'])['card']
        body={'request_id':str(uuid4()),'expected_revision':room['revision'],'offer_id':offer['offer_id'],'person_id':card['person_id']}
        assert http(root+'/picks',other,body,409)['error']['code']=='not_your_turn'
        saved=http(root+'/picks',owner,body)
        assert http(root+'/picks',owner,body)==saved
        stale=dict(body,request_id=str(uuid4()))
        assert http(root+'/picks',owner,stale,409)['error']['code']=='stale_room'
        room=http(root,other)
        assert len(room['members'])==turn+1
    assert room['state']=='complete' and room['draft']['status']=='production_finalized'
    assert len({v['person_id'] for v in room['draft']['picks']})==8
    assert room['draft']['budget']['talent_spend_usd']==sum(v['locked_fee_usd'] for v in room['members'])
    print(json.dumps({'check':'live two-player cooperative room','passed':True,'room_id':id,
        'draft_id':room['draft']['draft_id'],'picks':8,'unique_people':8,'snapshot_hash':room['draft']['snapshot_hash'],
        'websocket':'first-frame authentication and persisted snapshot passed',
        'note':'Created test guests and a synthetic finalized film. No release or timeout test was performed.'},indent=2))

if __name__=='__main__':main()
