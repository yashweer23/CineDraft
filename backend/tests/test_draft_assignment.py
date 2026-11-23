from itertools import product
import random
import pytest
from app.domain import Slot,SLOT_ROLES
from app.drafting.assignment import Talent,validate_pool,minimum_assignment,legal_candidates
from app.drafting.rules import choose_offer


def brute(pool,slots,used=frozenset()):
    choices=[[r for r in pool if r.role==SLOT_ROLES[s].value and r.person_id not in used] for s in slots]
    results=[(sum(r.fee_usd for r in rows),tuple(r.person_id for r in rows)) for rows in product(*choices) if len({r.person_id for r in rows})==len(slots)]
    return min(results) if results else None


def test_multirole_identity_trap_and_missing_matching():
    pool=[Talent('a','writer',100),Talent('a','composer',100),Talent('b','writer',400),Talent('c','composer',500)]
    result=minimum_assignment(pool,[Slot.WRITER,Slot.COMPOSER])
    assert result['cost_usd']==500
    assert [r['person_id'] for r in result['assignment']]==['b','a']
    assert minimum_assignment(pool[:2],[Slot.WRITER,Slot.COMPOSER]) is None


def test_four_actor_slots_need_four_distinct_identities():
    slots=[Slot.LEAD,Slot.CO_LEAD,Slot.SUPPORTING_1,Slot.SUPPORTING_2]
    pool=[Talent(str(i),'actor',100+i) for i in range(10)]
    assert minimum_assignment(pool,slots)['cost_usd']==406
    assert minimum_assignment(pool[:3],slots) is None


@pytest.mark.parametrize('seed',range(40))
def test_reduction_and_dp_match_exhaustive_assignments(seed):
    rng=random.Random(seed);slots=[Slot.DIRECTOR,Slot.LEAD,Slot.CO_LEAD,Slot.WRITER]
    pool=[Talent(f'p{i}',r,rng.randrange(1,20)) for i in range(8) for r in ('director','actor','writer') if rng.random()<.65]
    expected=brute(pool,slots,{'p0'} if seed%2 else set())
    result=minimum_assignment(pool,slots,{'p0'} if seed%2 else set())
    if expected is None:assert result is None
    else:
        assert result['cost_usd']==expected[0]
        assert tuple(x['person_id'] for x in result['assignment'])==expected[1]
    assert result==minimum_assignment(list(reversed(pool)),slots,{'p0'} if seed%2 else set())


def test_legal_candidate_optimization_matches_full_resolve_and_equality():
    pool=[Talent('a','director',50),Talent('a','writer',5),Talent('b','director',60),Talent('c','writer',20),Talent('d','composer',10)]
    for available in (59,60,79,80,90):
        for row in legal_candidates(pool,Slot.DIRECTOR,[Slot.WRITER,Slot.COMPOSER],set(),available):
            candidate=row['talent'];after=minimum_assignment(pool,[Slot.WRITER,Slot.COMPOSER],{candidate.person_id})
            assert row['selectable']==(after is not None and candidate.fee_usd+after['cost_usd']<=available)
    last=legal_candidates([Talent('x','composer',125000)],Slot.COMPOSER,[],set(),125000)[0]
    assert last['selectable'] and last['completion_cost_usd']==0
    assert not legal_candidates([Talent('x','composer',125001)],Slot.COMPOSER,[],set(),125000)[0]['selectable']


def test_no_remaining_slots_and_invalid_slot_lists():
    assert minimum_assignment([],[])=={'cost_usd':0,'assignment':[]}
    with pytest.raises(ValueError):minimum_assignment([],[Slot.LEAD,Slot.LEAD])


@pytest.mark.parametrize('pool',[[Talent('x','actor',-1)],[Talent('x','actor',True)],[Talent('x','actor',1.5)],[Talent('','actor',5)],[Talent('x','producer',5)],[Talent('x','actor',5),Talent('x','actor',5)]])
def test_bad_pool_is_rejected(pool):
    with pytest.raises(ValueError):validate_pool(pool)


def rows(count,legal):return [{'talent':Talent(f'p{i}','actor',100),'selectable':i in legal,'blocked_reason':None if i in legal else 'blocked'} for i in range(count)]

def test_offers_are_deterministic_prefer_legal_and_do_not_duplicate():
    data=rows(10,{0,1,2,3})
    a=choose_offer(data,'seed','stream');b=choose_offer(list(reversed(data)),'seed','stream')
    assert a==b and len({r['talent'].person_id for r in a})==3 and all(r['selectable'] for r in a)
    assert len(choose_offer(rows(2,{0}),'seed','stream'))==2


def test_reroll_maximizes_novelty_while_retaining_a_legal_choice():
    data=rows(7,{0});old={'p0','p1','p2'}
    offer=choose_offer(data,'seed','reroll',old)
    assert any(r['selectable'] for r in offer)
    assert sum(r['talent'].person_id not in old for r in offer)==2
    data=rows(7,{0,3})
    offer=choose_offer(data,'seed','reroll',old)
    assert sum(r['talent'].person_id not in old for r in offer)==3
    assert any(r['selectable'] for r in offer)
