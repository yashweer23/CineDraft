"""Exact minimum-cost distinct-person matching for at most eight slots."""
from collections import defaultdict
from dataclasses import dataclass
from app.domain import Role, Slot, SLOT_ROLES

@dataclass(frozen=True)
class Talent:
    person_id: str
    role: str
    fee_usd: int


def validate_pool(pool):
    seen=set()
    for row in pool:
        Role(row.role)
        if not row.person_id or type(row.fee_usd) is not int or row.fee_usd < 0:
            raise ValueError("Invalid talent identity or integer fee")
        key=(row.person_id,row.role)
        if key in seen: raise ValueError("Duplicate person-role price")
        seen.add(key)


def minimum_assignment(pool, slots, used=frozenset()):
    """Exact DP over slot masks; process each person once (not once per role).

    For k slots only the k cheapest unused people per role are needed: if an
    optimum uses a person outside that set, at least one of those k cheaper
    people is unused by the other k-1 slots and can replace them. Keep identity
    across roles. This is a reduction preserving optimality, not a heuristic.
    """
    slots=tuple(Slot(s) for s in slots)
    if len(slots)>8 or len(set(slots))!=len(slots): raise ValueError("Invalid remaining slots")
    if not slots: return {"cost_usd":0,"assignment":[]}
    slot_roles=tuple(SLOT_ROLES[s].value for s in slots)
    k=len(slots);roles=set(slot_roles);grouped=defaultdict(list)
    for row in pool:
        if row.person_id not in used and row.role in roles: grouped[row.role].append(row)
    by_person=defaultdict(dict)
    for role in sorted(roles):
        for row in sorted(grouped[role],key=lambda r:(r.fee_usd,r.person_id))[:k]:
            by_person[row.person_id][role]=row.fee_usd
    if len(by_person)<k:return None
    dp={0:(0,tuple('' for _ in slots))}
    for pid,prices in sorted(by_person.items()):
        # Hoist role lookup and occupied-bit construction out of the hot mask
        # loop. Preserve slot order, person order, and the exact witness tie-break.
        eligible=tuple((i,1<<i,prices[role]) for i,role in enumerate(slot_roles) if role in prices)
        before=list(dp.items())
        for mask,(cost,witness) in before:
            for i,bit,fee in eligible:
                if mask & bit:continue
                target=mask|bit;names=list(witness);names[i]=pid;candidate=(cost+fee,tuple(names))
                if target not in dp or candidate<dp[target]:dp[target]=candidate
    result=dp.get((1<<k)-1)
    if result is None:return None
    cost,names=result
    return {"cost_usd":cost,"assignment":[{"slot":s.value,"person_id":names[i],"fee_usd":by_person[names[i]][SLOT_ROLES[s].value]} for i,s in enumerate(slots)]}


def legal_candidates(pool, slot, remaining_slots, used, available):
    """Classify all candidates with at most k+1 exact solver calls.

    Removing a person outside an optimal witness cannot change its minimum
    cost. Only witness members require a fresh assignment calculation.
    """
    baseline=minimum_assignment(pool,remaining_slots,used)
    witness={r['person_id'] for r in baseline['assignment']} if baseline else set()
    result=[]
    for candidate in sorted((r for r in pool if r.role==SLOT_ROLES[Slot(slot)].value and r.person_id not in used),key=lambda r:r.person_id):
        completion=baseline
        if candidate.person_id in witness:
            completion=minimum_assignment(pool,remaining_slots,used|{candidate.person_id})
        if candidate.fee_usd>available:reason="Fee exceeds the available talent budget."
        elif completion is None:reason="This person is needed for another unfilled role; no unique complete roster remains."
        elif candidate.fee_usd+completion['cost_usd']>available:reason="The remaining roles cannot be completed within the talent budget."
        else:reason=None
        result.append({"talent":candidate,"selectable":reason is None,"blocked_reason":reason,
            "completion_cost_usd":completion['cost_usd'] if completion else None})
    return result
