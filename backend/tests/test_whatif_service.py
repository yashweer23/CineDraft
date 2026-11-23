"""Boundary checks before catalog reads or writes; transaction tests live separately."""
from types import SimpleNamespace as NS
from datetime import datetime,timezone
from uuid import UUID,uuid4
import pytest
from app.whatif import service
from app.whatif.example import example_inputs
from app.whatif.engine import compare
from app.whatif.schemas import CompareRequest
from app.drafting.assignment import Talent
from app.drafting.errors import DraftProblem
from app.simulation.example import synthetic_snapshot
from app.repository import canonical_hash

class NoReads:
    def get(self,*args):raise AssertionError('Unexpected catalog/database read')

@pytest.mark.parametrize('delta,code',[(1,'whatif_over_budget'),(100000000,'whatif_over_budget')])
def test_refund_budget_is_enforced_before_profile_read(monkeypatch,delta,code):
    f=synthetic_snapshot();pid=uuid4();available=f.draft.budget.talent_remaining_usd+f.draft.picks[0].locked_fee_usd
    monkeypatch.setattr(service,'pinned',lambda *args:[Talent(str(pid),'director',available+delta)])
    with pytest.raises(DraftProblem) as e:service.build_inputs(NoReads(),None,None,f,None,CompareRequest(request_id=uuid4(),slot='director',person_id=pid))
    assert e.value.code==code

@pytest.mark.parametrize('wrong',['duplicate','role','missing'])
def test_invalid_replacement_rejected_before_profile_read(monkeypatch,wrong):
    f=synthetic_snapshot();pid=f.draft.picks[1].person_id if wrong=='duplicate' else uuid4()
    monkeypatch.setattr(service,'pinned',lambda *args:[] if wrong=='missing' else [Talent(str(pid),'actor',100)])
    with pytest.raises(DraftProblem) as e:service.build_inputs(NoReads(),None,None,f,None,CompareRequest(request_id=uuid4(),slot='director',person_id=pid))
    assert e.value.code==('whatif_duplicate_person' if wrong=='duplicate' else 'whatif_invalid_replacement')


def test_embargo_checked_after_ownership_before_any_source_disclosure(monkeypatch):
    order=[]
    monkeypatch.setattr(service,'authorize',lambda *args:order.append('auth') or 'owner')
    monkeypatch.setattr(service.drafts,'owned',lambda *args,**kwargs:order.append('ownership') or (None,None,None))
    def embargo(*args):order.append('embargo');raise DraftProblem(423,'challenge_embargo','Hidden')
    monkeypatch.setattr(service,'guard_result',embargo)
    with pytest.raises(DraftProblem) as e:service.access(NoReads(),'token',uuid4())
    assert e.value.status==423 and order==['auth','ownership','embargo']

@pytest.mark.parametrize('corrupt',['input','output','identity'])
def test_saved_report_integrity_is_checked(corrupt):
    inputs=example_inputs();payload=inputs.model_dump(mode='json');outputs=compare(inputs)
    row=NS(id=uuid4(),draft_id=inputs.draft_id,slot='director',person_id=inputs.person_id,source_input_hash=inputs.source_input_hash,source_output_hash=inputs.source_output_hash,version='whatif-1.0',inputs=payload,input_hash=canonical_hash(payload),outputs=outputs,output_hash=canonical_hash(outputs),created_at=datetime.now(timezone.utc))
    assert service.checked(row)['comparison']==outputs
    if corrupt=='input':row.inputs['manifest']['samples']=65
    elif corrupt=='output':row.outputs['score']['delta']=999
    else:row.person_id=uuid4()
    with pytest.raises(DraftProblem) as e:service.checked(row)
    assert e.value.status==503 and e.value.code=='whatif_integrity'
