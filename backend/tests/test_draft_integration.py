"""Real PostgreSQL transactions and ownership. All source data is synthetic."""
from datetime import datetime,timedelta,timezone
from uuid import UUID,uuid4
import pytest
from alembic import command
from sqlalchemy import select,text,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from app import models as m,contracts as w
from app.domain import GENRES
from app.fixtures import fixture_id,seed_fixture,DATASET,DRAFT_ID
from app.repository import canonical_hash,load_snapshot
from app.talent.service import build as build_talent
from app.collaboration.service import build as build_graph
from app.drafting.catalog import prepare,availability
from app.drafting import service,auth
from app.drafting.errors import DraftProblem
from app.main import create_app
from test_foundation import settings,FakeDatabase
from test_persistence import database
pytestmark=pytest.mark.integration


def seed(c):
    dataset='fixture:draft-v1';config={'synthetic':True,'purpose':'Phase 7 transaction tests'}
    with Session(c) as s,s.begin():
        ds=m.DatasetVersion(id=dataset,configuration=config,content_hash=canonical_hash(config),scope_version='fixture:scope',role_mapping_version='fixture:roles',provenance={'source':'fixture'})
        s.add(ds);s.flush()
        for key,name in GENRES.items():s.add(m.Genre(id=key,name=name))
        mid=fixture_id('draft-film');s.add(m.Movie(id=mid,source='fixture',source_key='fixture:draft-film'));s.flush()
        s.add(m.MovieSnapshot(dataset_id=dataset,movie_id=mid,title='Synthetic Draft Film',runtime_minutes=90,eligibility='eligible',eligibility_reason='Synthetic',provenance={'source':'fixture'}));s.flush()
        s.add(m.MovieGenre(dataset_id=dataset,movie_id=mid,genre_id='drama'))
        for role,count,job in [('director',5,'Director'),('actor',8,'Actor'),('writer',3,'Screenplay'),('cinematographer',3,'Director of Photography'),('composer',3,'Original Music Composer')]:
            for i in range(count):
                key=f'draft-{role}-{i}';pid=fixture_id(key)
                s.add(m.Person(id=pid,source='fixture',source_key='fixture:'+key));s.flush()
                s.add(m.PersonSnapshot(dataset_id=dataset,person_id=pid,name=f'Synthetic {role} {i}',popularity=i*10,coverage={'synthetic':True}));s.flush()
                s.add(m.Credit(dataset_id=dataset,person_id=pid,movie_id=mid,dedupe_key=key,kind='cast' if role=='actor' else 'crew',role=role,job=job,provenance={'source':'fixture'}));s.flush()
        # The same physical person can also compose, but can only be picked once.
        s.add(m.Credit(dataset_id=dataset,person_id=fixture_id('draft-writer-0'),movie_id=mid,dedupe_key='draft-cross-role',kind='crew',role='composer',job='Original Music Composer',provenance={'source':'fixture'}));s.flush()
        ds.sealed=True
    build_talent(c,dataset,'draft-v1');build_graph(c,dataset,'draft-v1')
    prepare(c,'pricing:draft-v1','graph:draft-v1','draft-v1',activate=True)


@pytest.fixture
def game(database):
    c=database[0];seed(c);token=auth.create_session(c)['access_token']
    d=service.create(c,token,w.CreateDraftRequest(request_id=uuid4(),genre_id='drama',tier='blockbuster'))
    return c,token,d


def action(c,token,d,cmd,cls=w.MutationRequest,**fields):
    body=cls(request_id=uuid4(),expected_revision=d['revision'],**fields)
    return service.mutate(c,token,UUID(d['draft_id']),cmd,body)


def pick_body(d):
    offer=d['current_offer'];person=next(x['card']['person_id'] for x in offer['candidates'] if x['selectable'])
    return w.PickRequest(request_id=uuid4(),expected_revision=d['revision'],offer_id=offer['offer_id'],person_id=person)


def complete(c,token,d):
    while d['status']=='awaiting_pick':
        d=service.mutate(c,token,UUID(d['draft_id']),'pick',pick_body(d))
        assert len({p['person_id'] for p in d['picks']})==len(d['picks'])
        assert sum(p['locked_fee_usd'] for p in d['picks'])==d['budget']['talent_spend_usd']
        assert d['minimum_remaining_cost_usd']<=d['budget']['talent_remaining_usd']
    return d


def test_create_idempotency_owner_isolation_and_server_pins(game):
    c,t,d=game;body=w.CreateDraftRequest(request_id=uuid4(),genre_id='horror',tier='blockbuster')
    first=service.create(c,t,body);assert service.create(c,t,body)==first
    with pytest.raises(DraftProblem,match='different body'):service.create(c,t,body.model_copy(update={'genre_id':'drama'}))
    other=auth.create_session(c)['access_token'];assert service.list_drafts(c,other)['items']==[]
    with pytest.raises(DraftProblem) as e:service.read(c,other,UUID(d['draft_id']))
    assert e.value.status==404
    with pytest.raises(DraftProblem) as e:service.mutate(c,other,UUID(d['draft_id']),'pick',pick_body(d))
    assert e.value.status==404
    assert len(service.list_drafts(c,t)['items'])==2
    assert service.list_drafts(c,t,1)['next_offset']==1
    assert d['versions']['graph_id']=='graph:draft-v1' and d['versions']['catalog_id']=='draft-catalog:draft-v1'
    assert d['synthetic'] and all(x['card']['source']=='fixture' for x in d['current_offer']['candidates'])
    with Session(c) as s:
        owner=s.scalar(select(m.GuestSession));assert owner.token_hash==auth.token_hash(t) and owner.token_hash!=t
        assert t not in str(s.scalar(select(m.DraftRuntime.creation_response)))


def test_pick_retry_stale_revision_offer_and_forged_person_preserve_state(game):
    c,t,d=game;body=pick_body(d);after=service.mutate(c,t,UUID(d['draft_id']),'pick',body)
    assert service.mutate(c,t,UUID(d['draft_id']),'pick',body)==after
    with pytest.raises(DraftProblem,match='different body'):service.mutate(c,t,UUID(d['draft_id']),'pick',body.model_copy(update={'person_id':uuid4()}))
    with pytest.raises(DraftProblem) as e:service.mutate(c,t,UUID(d['draft_id']),'pick',body.model_copy(update={'request_id':uuid4()}))
    assert e.value.code=='stale_revision'
    with pytest.raises(DraftProblem) as e:service.mutate(c,t,UUID(d['draft_id']),'pick',body.model_copy(update={'request_id':uuid4(),'expected_revision':after['revision']}))
    assert e.value.code=='stale_offer'
    invalid=pick_body(after).model_copy(update={'person_id':uuid4()})
    with pytest.raises(DraftProblem) as e:service.mutate(c,t,UUID(d['draft_id']),'pick',invalid)
    assert e.value.code=='invalid_candidate'
    assert service.read(c,t,UUID(d['draft_id']))==after
    with Session(c) as s:assert s.scalar(select(func.count()).select_from(m.ActionRecord))==1


def test_rerolls_replace_offer_at_most_twice_and_replay_is_free(game):
    c,t,d=game
    for count in (1,2):
        old=d['current_offer'];body=w.RerollRequest(request_id=uuid4(),expected_revision=d['revision'],offer_id=old['offer_id'])
        d=service.mutate(c,t,UUID(d['draft_id']),'reroll',body)
        assert service.mutate(c,t,UUID(d['draft_id']),'reroll',body)==d
        assert d['rerolls_used']==count and d['budget']['talent_spend_usd']==0
        oldids={x['card']['person_id'] for x in old['candidates']};newids={x['card']['person_id'] for x in d['current_offer']['candidates']}
        assert len(newids-oldids)==2  # 5 directors: maximum fresh identities is two.
    assert not d['can_reroll']
    with pytest.raises(DraftProblem):action(c,t,d,'reroll',w.RerollRequest,offer_id=d['current_offer']['offer_id'])


def test_short_pool_reroll_rejected_without_consuming_allowance(database):
    c=database[0]
    with Session(c) as s,s.begin():seed_fixture(s)
    build_talent(c,DATASET,'short');build_graph(c,DATASET,'short');prepare(c,'pricing:short','graph:short','short',activate=True)
    t=auth.create_session(c)['access_token'];d=service.create(c,t,w.CreateDraftRequest(request_id=uuid4(),genre_id='drama',tier='blockbuster'))
    assert len(d['current_offer']['candidates'])==1 and not d['can_reroll']
    with pytest.raises(DraftProblem) as e:action(c,t,d,'reroll',w.RerollRequest,offer_id=d['current_offer']['offer_id'])
    assert e.value.code=='reroll_unavailable'
    assert service.read(c,t,UUID(d['draft_id']))==d
    with Session(c) as s:assert load_snapshot(s,DRAFT_ID).schema_version=='phase3-v1'


def test_cached_recast_cancel_confirm_refund_and_finalized_snapshot(game):
    c,t,d=game;d=complete(c,t,d);before=d
    preview=action(c,t,d,'preview_recast',w.RecastPreviewRequest,slot='director');cached=preview['current_offer']
    with pytest.raises(DraftProblem):action(c,t,preview,'finalize')
    d=action(c,t,preview,'cancel_recast',w.RecastCancelRequest,offer_id=cached['offer_id'])
    # Another slot has an independent cached preview.
    other=action(c,t,d,'preview_recast',w.RecastPreviewRequest,slot='writer')
    d=action(c,t,other,'cancel_recast',w.RecastCancelRequest,offer_id=other['current_offer']['offer_id'])
    d=action(c,t,d,'preview_recast',w.RecastPreviewRequest,slot='director')
    assert d['current_offer']['offer_id']==cached['offer_id'] and d['current_offer']['candidates']==cached['candidates']
    assert d['current_offer']['revision']==d['revision']>d['current_offer']['generated_at_revision']
    assert d['picks']==before['picks'] and d['budget']==before['budget'] and d['recasts_used']==0
    candidate=next(x['card'] for x in d['current_offer']['candidates'] if x['selectable'])
    old=before['picks'][0]
    d=action(c,t,d,'confirm_recast',w.RecastConfirmRequest,offer_id=cached['offer_id'],person_id=candidate['person_id'])
    assert d['status']=='review_locked' and d['recasts_used']==1
    assert d['budget']['talent_spend_usd']==before['budget']['talent_spend_usd']-old['locked_fee_usd']+candidate['hiring_fee_usd']
    assert len({p['person_id'] for p in d['picks']})==8
    with pytest.raises(DraftProblem):action(c,t,d,'preview_recast',w.RecastPreviewRequest,slot='writer')
    body=w.MutationRequest(request_id=uuid4(),expected_revision=d['revision'])
    final=service.mutate(c,t,UUID(d['draft_id']),'finalize',body)
    assert service.mutate(c,t,UUID(d['draft_id']),'finalize',body)==final
    assert final['status']=='production_finalized' and len(final['snapshot_hash'])==64
    with Session(c) as s:
        snapshot=load_snapshot(s,UUID(d['draft_id']))
        assert snapshot.schema_version=='phase7-v1' and len(snapshot.collaborations)==12
        assert all(edge['shared_movie_count']==1 and len(edge['evidence'])==1 for edge in snapshot.collaborations)
        assert snapshot.draft.versions.graph_hash==s.get(m.GraphVersion,'graph:draft-v1').content_hash
        assert s.get(m.Result,UUID(d['draft_id'])) is None
        with pytest.raises(IntegrityError),s.begin_nested():s.execute(text('UPDATE picks SET locked_fee_usd=0'))
    with pytest.raises(DraftProblem):action(c,t,final,'abandon')


def test_receipt_failure_rolls_back_pick_offer_and_money(game):
    c,t,d=game
    c.execute(text("CREATE FUNCTION fail_receipt() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text('CREATE TRIGGER fail_receipt BEFORE INSERT ON action_records FOR EACH ROW EXECUTE FUNCTION fail_receipt()'))
    with pytest.raises(IntegrityError):service.mutate(c,t,UUID(d['draft_id']),'pick',pick_body(d))
    assert service.read(c,t,UUID(d['draft_id']))==d
    with Session(c) as s:
        assert s.scalar(select(func.count()).select_from(m.Offer))==1
        assert s.scalar(select(func.count()).select_from(m.Pick))==0


def test_snapshot_failure_rolls_back_finalization(game):
    c,t,d=game;d=complete(c,t,d)
    c.execute(text("CREATE FUNCTION fail_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure' USING ERRCODE='23514'; END $$"))
    c.execute(text('CREATE TRIGGER fail_snapshot BEFORE INSERT ON draft_snapshots FOR EACH ROW EXECUTE FUNCTION fail_snapshot()'))
    with pytest.raises(IntegrityError):action(c,t,d,'finalize')
    assert service.read(c,t,UUID(d['draft_id']))==d


def test_catalog_dry_run_reactivation_pins_and_mismatches(game):
    c,t,d=game
    report=prepare(c,'pricing:draft-v1','graph:draft-v1','new',dry_run=True,activate=True)
    assert not report['created'] and not report['activated']
    assert availability(c)['catalog_id']=='draft-catalog:draft-v1'
    prepare(c,'pricing:draft-v1','graph:draft-v1','new',activate=True)
    assert availability(c)['catalog_id']=='draft-catalog:new'
    assert service.read(c,t,UUID(d['draft_id']))['versions']==d['versions']
    with Session(c) as s,s.begin():seed_fixture(s)
    build_graph(c,DATASET,'other-dataset')
    with pytest.raises(ValueError,match='same sealed dataset'):prepare(c,'pricing:draft-v1','graph:other-dataset','bad')
    with pytest.raises(ValueError,match='computed'):prepare(c,'fixture:pricing-v1','graph:other-dataset','bad')


def test_expired_revoked_unknown_sessions_and_immutable_ownership(game):
    c,t,d=game;expired='e'*43
    with Session(c) as s,s.begin():
        s.add(m.GuestSession(token_hash=auth.token_hash(expired),expires_at=datetime.now(timezone.utc)-timedelta(days=1)))
        with pytest.raises(IntegrityError),s.begin_nested():s.execute(text("UPDATE draft_runtime SET creation_body_hash=repeat('0',64)"))
    for invalid in (expired,'u'*43):
        with pytest.raises(DraftProblem) as e:service.read(c,invalid,UUID(d['draft_id']))
        assert e.value.status==401
    auth.revoke_session(c,t)
    with pytest.raises(DraftProblem) as e:service.mutate(c,t,UUID(d['draft_id']),'pick',pick_body(d))
    assert e.value.status==401


def test_abandon_retains_history_and_refuses_later_actions(game):
    c,t,d=game;body=w.MutationRequest(request_id=uuid4(),expected_revision=d['revision'])
    d=service.mutate(c,t,UUID(d['draft_id']),'abandon',body)
    assert d['status']=='abandoned' and d['current_offer'] is None
    assert service.mutate(c,t,UUID(d['draft_id']),'abandon',body)==d
    with pytest.raises(DraftProblem):action(c,t,d,'finalize')
    assert service.list_drafts(c,t)['items'][0]==d


def test_phase7_history_blocks_downgrade(game,database):
    c,t,d=game
    with pytest.raises(IntegrityError),c.begin_nested():command.downgrade(database[1],'0003_phase6')
    assert service.read(c,t,UUID(d['draft_id']))==d


def test_http_create_pick_replay_and_foreign_owner(game):
    c,t,d=game;db=FakeDatabase();db.engine=c;app=create_app(settings(),db)
    headers={'Authorization':'Bearer '+t};base='/api/v1/drafts/'+d['draft_id']
    with TestClient(app) as client:
        body=pick_body(d).model_dump(mode='json')
        first=client.post(base+'/picks',headers=headers,json=body)
        assert first.status_code==200,first.text
        assert first.headers['cache-control']=='no-store'
        assert client.post(base+'/picks',headers=headers,json=body).json()==first.json()
        assert client.get(base).status_code==401
        other=client.post('/api/v1/sessions').json()['access_token']
        assert client.get(base,headers={'Authorization':'Bearer '+other}).status_code==404
        forged=client.post(base+'/picks',headers=headers,json=body|{'fee_usd':0})
        assert forged.status_code==422
        assert client.get(base,headers=headers).json()==first.json()
