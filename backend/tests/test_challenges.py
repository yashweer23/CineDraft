from datetime import date,timedelta,timezone
from types import SimpleNamespace
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.challenges import policy,schemas as w,service

@pytest.mark.parametrize('day,zone,hours',[('2026-10-31','Asia/Kolkata',24),('2026-03-08','America/New_York',23),('2026-11-01','America/New_York',25)])
def test_calendar_boundaries_and_dst(day,zone,hours):
    opens,closes=policy.window(date.fromisoformat(day),zone)
    assert closes-opens==timedelta(hours=hours) and opens.tzinfo==timezone.utc
    assert policy.phase(opens,closes,opens-timedelta(microseconds=1))=='scheduled'
    assert policy.phase(opens,closes,opens)=='open'
    assert policy.phase(opens,closes,closes-timedelta(microseconds=1))=='open'
    assert policy.phase(opens,closes,closes)=='closed'

def test_invalid_zone_and_forged_attempt_inputs():
    with pytest.raises(ValueError):policy.window(date.today(),'No/Such_Zone')
    for key,value in [('seed','x'),('catalog_id','other'),('studio_score',100),('genre_id','comedy'),('tier','indie')]:
        with pytest.raises(ValidationError):w.Begin(request_id=uuid4(),**{key:value})

def test_public_projection_hides_seed():
    opens,closes=policy.window(date(2026,10,31),'Asia/Kolkata');seed='ab'*32
    c=SimpleNamespace(id='day-1',opens_at=opens,closes_at=closes,timezone='Asia/Kolkata',genre_id='drama',tier='indie',catalog_id='catalog:1',configuration={'synthetic':True},config_hash='f'*64,seed=seed,seed_commitment=policy.commitment(seed))
    public=service.public(c,opens)
    assert seed not in str(public) and 'seed' not in public
    assert w.ChallengeView.model_validate(public).results_hidden and not service.public(c,closes)['results_hidden']
    assert policy.commitment(seed)!=policy.commitment('ac'*32)
