"""PostgreSQL is the room authority; every command locks room, then draft."""
from datetime import timedelta
import hashlib
import hmac
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models as m, contracts as c
from app.drafting import service as drafts
from app.drafting.auth import authorize
from app.drafting.catalog import checked_catalog
from app.drafting.schemas import LiveCard
from app.accounts.service import Principal
from app.repository import canonical_hash
from app.rooms import schemas as w
from app.rooms.policy import require_pick, timeout_choice


def now(s):
    return s.scalar(select(func.clock_timestamp()))


def invite_hash(body):
    return hashlib.sha256(body.invite_code.get_secret_value().encode('ascii')).hexdigest()


def digest(command, body):
    data = body.model_dump(mode='json', exclude={'invite_code'})
    if hasattr(body, 'invite_code'):
        data['invite_hash'] = invite_hash(body)
    return canonical_hash({'command': command, 'body': data})


def owner_ids(s, owner):
    if isinstance(owner, Principal):
        return set(s.scalars(select(m.AccountOwnership.guest_session_id).where(m.AccountOwnership.account_id == owner.account_id)))
    return {owner.id}


def seat_for(s, room, owner):
    ids = owner_ids(s, owner)
    if room.host_id in ids:
        return 0
    if room.guest_id in ids:
        return 1
    drafts.fail('Room not found for this session.', 'room_not_found', status=404)


def locked(s, room_id):
    room = s.scalar(select(m.DraftRoom).where(m.DraftRoom.id == room_id).with_for_update())
    if room is None:
        drafts.fail('Room not found for this session.', 'room_not_found', status=404)
    return room


def game(s, room):
    d = s.scalar(select(m.Draft).where(m.Draft.id == room.draft_id).with_for_update())
    rt = s.get(m.DraftRuntime, room.draft_id)
    return d, rt, checked_catalog(s, rt.catalog_id)


def view(s, room, seat, bundle=None):
    d, rt, catalog = bundle or game(s, room)
    members = []
    for pick in drafts.picks_for(s, d):
        candidate = s.get(m.OfferCandidate, (pick.offer_id, pick.person_id))
        members.append(dict(slot=pick.slot, locked_fee_usd=pick.locked_fee_usd,
                            card=LiveCard.model_validate(candidate.card_snapshot)))
    return w.RoomView(room_id=room.id, revision=room.revision, state=room.state, seat=seat,
        guest_joined=room.guest_id is not None, turn_seat=len(members) % 2 if room.state == 'active' else None,
        turn_seconds=room.turn_seconds, deadline=room.deadline, server_time=now(s),
        draft=drafts.view(s, d, rt, catalog), members=members, events=room.events).model_dump(mode='json')


def create(engine, token, body):
    with Session(engine) as s, s.begin():
        owner = authorize(s, token, exclusive=True)
        checksum = digest('create', body)
        prior = s.scalar(select(m.DraftRoom).where(m.DraftRoom.host_id.in_(owner_ids(s, owner)),
            m.DraftRoom.creation_request_id == body.request_id))
        if prior:
            if prior.creation_hash != checksum:
                drafts.fail('Creation request ID was reused with another body.', 'idempotency_conflict')
            return prior.creation_response
        # Namespace the solo creation request so it cannot attach an earlier solo film.
        request_id = uuid5(NAMESPACE_URL, f'cinedraft:room:{owner.id}:{body.request_id}')
        if s.scalar(select(m.DraftRuntime.draft_id).where(m.DraftRuntime.session_id == owner.id,
                m.DraftRuntime.creation_request_id == request_id)):
            drafts.fail('The internal draft request already exists.', 'idempotency_conflict')
        draft = drafts.create_in_session(s, owner, c.CreateDraftRequest(request_id=request_id,
            genre_id=body.genre_id, tier=body.tier))
        room = m.DraftRoom(draft_id=UUID(draft['draft_id']), host_id=owner.id, invite_hash=invite_hash(body),
            creation_request_id=body.request_id, creation_hash=checksum, creation_response={},
            state='waiting', revision=0, turn_seconds=body.turn_seconds, events=[])
        s.add(room); s.flush()
        result = view(s, room, 0)
        room.creation_response = result
        return result


def read(engine, token, room_id):
    with Session(engine) as s, s.begin():
        owner = authorize(s, token)
        room = locked(s, room_id)
        return view(s, room, seat_for(s, room, owner))


def save_receipt(s, room, actor_id, body, checksum, result):
    s.add(m.RoomReceipt(room_id=room.id, request_id=body.request_id, actor_id=actor_id,
                       body_hash=checksum, response=result))
    s.flush()
    return result


def prior_receipt(s, room, owner, body, checksum):
    prior = s.get(m.RoomReceipt, (room.id, body.request_id))
    if prior:
        if prior.actor_id not in owner_ids(s, owner) or prior.body_hash != checksum:
            drafts.fail('Request ID was reused for another action.', 'idempotency_conflict')
        return prior.response
    return None


def join(engine, token, room_id, body):
    with Session(engine) as s, s.begin():
        owner = authorize(s, token)
        room = locked(s, room_id)
        if not hmac.compare_digest(room.invite_hash, invite_hash(body)):
            drafts.fail('Room or invitation is unavailable.', 'invalid_invitation', status=404)
        checksum = digest('join', body)
        prior = prior_receipt(s, room, owner, body, checksum)
        if prior:
            return prior
        ids = owner_ids(s, owner)
        if room.host_id in ids:
            drafts.fail('Use a different session for your partner.', 'same_player')
        if room.guest_id in ids:
            return save_receipt(s, room, room.guest_id, body, checksum, view(s, room, 1))
        if room.state != 'waiting' or room.guest_id is not None:
            drafts.fail('This room already has two players or is closed.', 'room_full')
        room.guest_id = owner.id
        room.revision += 1
        s.flush()
        return save_receipt(s, room, owner.id, body, checksum, view(s, room, 1))


def apply_pick(s, room, bundle, person_id, offer_id, *, automatic):
    d, rt, catalog = bundle
    count = len(drafts.picks_for(s, d))
    offer = s.get(m.Offer, offer_id)
    body = c.PickRequest(request_id=uuid4(), expected_revision=d.revision, offer_id=offer_id, person_id=person_id)
    drafts.mutate_in_session(s, d, rt, catalog, 'pick', body)
    room.events = [*room.events, dict(turn=count + 1, seat=count % 2, slot=offer.slot,
                                     person_id=str(person_id), automatic=automatic)]
    room.revision += 1
    if count == 7:
        drafts.mutate_in_session(s, d, rt, catalog, 'finalize', c.MutationRequest(request_id=uuid4(), expected_revision=d.revision))
        room.state = 'complete'
        room.deadline = None
    else:
        # A late worker grants a fresh full turn; no cascade of missed picks after downtime.
        room.deadline = now(s) + timedelta(seconds=room.turn_seconds)
    s.flush()


def command(engine, token, room_id, name, body):
    with Session(engine) as s, s.begin():
        owner = authorize(s, token)
        room = locked(s, room_id)
        seat = seat_for(s, room, owner)
        checksum = digest(name, body)
        prior = prior_receipt(s, room, owner, body, checksum)
        if prior:
            return prior
        if room.revision != body.expected_revision:
            drafts.fail('Room changed. Refresh before a new action.', 'stale_room', room.revision)
        bundle = game(s, room)
        d, rt, catalog = bundle
        if name == 'pick':
            require_pick(room.state, room.revision, body.expected_revision, seat,
                         len(drafts.picks_for(s, d)), room.deadline, now(s))
            apply_pick(s, room, bundle, body.person_id, body.offer_id, automatic=False)
        elif name == 'start':
            if seat != 0 or room.state != 'waiting' or room.guest_id is None:
                drafts.fail('Only the host can start after the partner joins.', 'cannot_start')
            deadline = now(s) + timedelta(seconds=room.turn_seconds)
            room.state = 'active'; room.revision += 1
            room.deadline = deadline
        elif name == 'cancel':
            if seat != 0 or room.state not in ('waiting', 'active'):
                drafts.fail('Only the host can cancel an unfinished room.', 'cannot_cancel')
            drafts.mutate_in_session(s, d, rt, catalog, 'abandon', c.MutationRequest(request_id=uuid4(), expected_revision=d.revision))
            room.state = 'cancelled'; room.revision += 1; room.deadline = None
        else:
            drafts.fail('Unsupported room action.', status=422)
        s.flush()
        return save_receipt(s, room, room.host_id if seat == 0 else room.guest_id,
                            body, checksum, view(s, room, seat, bundle))


def advance_due(engine):
    """One bounded sweep; SKIP LOCKED allows multiple API processes safely."""
    advanced = 0
    with Session(engine) as s, s.begin():
        rooms = s.scalars(select(m.DraftRoom).where(m.DraftRoom.state == 'active',
            m.DraftRoom.deadline <= func.clock_timestamp()).order_by(m.DraftRoom.deadline, m.DraftRoom.id)
            .limit(20).with_for_update(skip_locked=True)).all()
        for room in rooms:
            # Isolate a malformed catalog/room so other deadlines still progress.
            try:
                with s.begin_nested():
                    bundle = game(s, room)
                    d, rt, _ = bundle
                    candidates = s.scalars(select(m.OfferCandidate).where(m.OfferCandidate.offer_id == rt.current_offer_id)).all()
                    candidate = timeout_choice(candidates)
                    apply_pick(s, room, bundle, candidate.person_id, rt.current_offer_id, automatic=True)
                    advanced += 1
            except Exception:
                import logging
                logging.getLogger('cinedraft').error('Room timeout failed; room_id=%s', room.id)
    return advanced
