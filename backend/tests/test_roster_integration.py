from uuid import UUID,uuid4
from sqlalchemy.orm import Session
import pytest
from app import contracts as w
from app.repository import load_snapshot,canonical_hash
from app.drafting import service,auth
from app.drafting.errors import DraftProblem
from app.simulation import service as releases
from test_persistence import database
from test_draft_integration import game,complete,action,pick_body
pytestmark=pytest.mark.integration


def test_roster_reads_exact_saved_card_after_pick_and_recast(game):
    c,t,d=game
    assert service.roster(c,t,UUID(d['draft_id']))['members']==[]
    choice=next(x['card'] for x in d['current_offer']['candidates'] if x['selectable'])
    d=service.mutate(c,t,UUID(d['draft_id']),'pick',pick_body(d))
    r=service.roster(c,t,UUID(d['draft_id']))
    assert r['revision']==d['revision'] and r['members'][0]['card']==choice
    d=complete(c,t,d)
    old=service.roster(c,t,UUID(d['draft_id']))['members']
    d=action(c,t,d,'preview_recast',w.RecastPreviewRequest,slot='director')
    assert service.roster(c,t,UUID(d['draft_id']))['members']==old
    replacement=next(x['card'] for x in d['current_offer']['candidates'] if x['selectable'])
    d=action(c,t,d,'confirm_recast',w.RecastConfirmRequest,offer_id=d['current_offer']['offer_id'],person_id=replacement['person_id'])
    r=service.roster(c,t,UUID(d['draft_id']))
    assert r['members'][0]['card']==replacement
    assert sum(x['locked_fee_usd'] for x in r['members'])==d['budget']['talent_spend_usd']


def test_roster_remains_read_only_after_release_and_denies_other_owners(game):
    c,t,d=game;d=complete(c,t,d);d=action(c,t,d,'finalize')
    draft_id=UUID(d['draft_id'])
    with Session(c) as s:before=canonical_hash(load_snapshot(s,draft_id).model_dump(mode='json'))
    releases.release(c,t,draft_id,'release',w.MutationRequest(request_id=uuid4(),expected_revision=d['revision']))
    r=service.roster(c,t,draft_id)
    assert len(r['members'])==8 and r==service.roster(c,t,draft_id)
    with Session(c) as s:assert canonical_hash(load_snapshot(s,draft_id).model_dump(mode='json'))==before
    other=auth.create_session(c)['access_token']
    with pytest.raises(DraftProblem) as error:service.roster(c,other,draft_id)
    assert error.value.status==404
    auth.revoke_session(c,t)
    with pytest.raises(DraftProblem) as error:service.roster(c,t,draft_id)
    assert error.value.status==401
