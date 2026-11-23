"""Pure turn policy; browser timers never authorize commands."""
from app.drafting.errors import DraftProblem

def require_pick(state, revision, expected, seat, count, deadline, now):
    if revision != expected:
        raise DraftProblem(409, 'stale_room', 'Room changed. Refresh before making a new choice.', revision)
    if state != 'active':
        raise DraftProblem(409, 'room_inactive', 'The room is not drafting.')
    if deadline is None or now >= deadline:
        raise DraftProblem(409, 'turn_expired', 'This turn has expired. Refresh for the automatic pick.')
    if seat != count % 2:
        raise DraftProblem(409, 'not_your_turn', 'Wait for your partner to pick.')

def timeout_choice(candidates):
    available = [row for row in candidates if row.selectable]
    if not available:
        raise DraftProblem(503, 'no_continuation', 'No legal timeout choice. The room was preserved.')
    return min(available, key=lambda row: (row.fee_usd, str(row.person_id)))
