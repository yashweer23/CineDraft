"""Generated cross-role equivalence and production-engine accounting checks."""
import random
from decimal import Decimal
import pytest
from app.domain import GENRES, TIERS, Role, Slot, SLOT_ROLES
from app.drafting.assignment import Talent,minimum_assignment,legal_candidates
from app.validation import assignment_phase12 as old
from app.validation.corpus import STRATEGIES,draft,catalog
from app.simulation.engine import simulate
from app.repository import canonical_hash

@pytest.mark.parametrize('seed',range(80))
def test_exact_cost_witness_and_offer_classification_match_phase12(seed):
    rng=random.Random(seed)
    pool=[Talent(f'p{i:02}',r.value,rng.randrange(0,8)*25000) for i in range(3+seed%25)
          for r in Role if rng.random()<.5]
    slots=rng.sample(list(Slot),1+seed%8);used={'p00','p02'} if seed%2 else set()
    assert minimum_assignment(pool,slots,used)==old.minimum_assignment(pool,slots,used)
    available=rng.randrange(0,40)*25000
    assert legal_candidates(pool,slots[0],slots[1:],used,available)==old.legal_candidates(pool,slots[0],slots[1:],used,available)
    assert minimum_assignment(pool,slots,used)==minimum_assignment(list(reversed(pool)),slots,used)

@pytest.mark.parametrize('genre',list(GENRES))
@pytest.mark.parametrize('tier',list(TIERS))
@pytest.mark.parametrize('strategy',STRATEGIES)
def test_generated_draft_all_briefs_exact_replay_and_money(genre,tier,strategy):
    frozen,result,trace=draft('regression:13',genre,tier,strategy)
    budget=frozen.draft.budget;picks=frozen.draft.picks
    assert len({p.person_id for p in picks})==8
    assert budget.talent_spend_usd==sum(p.locked_fee_usd for p in picks)
    assert budget.reserve_usd==TIERS[tier]*35//100
    assert budget.talent_remaining_usd>=0
    assert all(t['selected'] in t['selectable'] and t['remaining_usd']>=0 for t in trace)
    assert all(c.role==SLOT_ROLES[p.slot] for p,c in zip(picks,frozen.cards))
    assert result['production_cost_usd']==budget.reserve_usd+budget.talent_spend_usd
    assert sum(result['weekly_gross_usd'])==result['worldwide_gross_usd']
    assert result['profit_usd']==result['studio_receipts_usd']-result['total_cost_usd']
    assert 0<=Decimal(result['studio_score_unrounded'])<=100
    reverse,again,trace2=draft('regression:13',genre,tier,strategy,reverse_pool=True)
    assert frozen==reverse and result==again and trace==trace2

@pytest.mark.parametrize('missing_role',list(Role))
def test_fully_depleted_role_never_appears_completable(missing_role):
    pool,_,_=catalog();pool=[t for t in pool if t.role!=missing_role.value]
    assert minimum_assignment(pool,list(Slot)) is None


def test_reference_remains_the_exact_phase12_source():
    # Pin copied code: it is never imported by the API or used as a fallback.
    import hashlib
    from pathlib import Path
    assert hashlib.sha256(Path(old.__file__).read_bytes()).hexdigest()=='2a929ec2be8b0a59f60b581e128385f1d06da8fe8c23e014a1fd7271dcfebad6'

@pytest.mark.parametrize('tier',list(TIERS))
def test_generated_brief_original_pick_is_exact_paired_control(tier):
    from app.whatif.engine import project,compare,MANIFEST
    from app.whatif.schemas import Inputs
    frozen,result,_=draft('control:13','science_fiction',tier,'genre_greedy')
    baseline=project(frozen);before=canonical_hash(result)
    inputs=Inputs(draft_id=frozen.draft.draft_id,source_input_hash=canonical_hash(frozen.model_dump(mode='json')),
        source_output_hash=before,slot='director',person_id=frozen.draft.picks[0].person_id,manifest=MANIFEST,
        baseline=baseline,alternative=baseline.model_copy(deep=True),evidence_movies={})
    report=compare(inputs)
    assert Decimal(report['score']['unrounded_delta'])==0 and report['unchanged'] and report['sample_count']==64
    assert all(all(Decimal(v)==0 for v in metric['paired_delta'].values()) and metric['equal_samples']==64 for metric in report['metrics'])
    assert canonical_hash(result)==before
