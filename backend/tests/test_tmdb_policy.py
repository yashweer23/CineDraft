from copy import deepcopy
from datetime import date
import pytest
from pydantic import ValidationError
from app.tmdb.payloads import MoviePayload, CreditPayload, ReviewOverride, image_url, ConfigurationPayload
from app.tmdb.policy import classify,credit_role,normalize_credits
from tmdb_fixtures import movie,CONFIG

CUTOFF=date(2026,1,1)

def test_known_narrative_film_and_null_ratings_are_supported():
    value=MoviePayload.model_validate(movie(vote_average=None,vote_count=0,poster_path=None))
    assert classify(value,CUTOFF)["status"]=="eligible"
    assert value.vote_average is None

@pytest.mark.parametrize("changes,status",[
 ({"original_language":"fr"},"excluded"),({"status":"Planned"},"excluded"),
 ({"release_date":"2027-01-01"},"excluded"),({"runtime":59},"excluded"),
 ({"genres":[{"id":99,"name":"Documentary"}]},"excluded"),
 ({"genres":[{"id":10770,"name":"TV Movie"}]},"excluded"),
 ({"runtime":None},"review"),({"runtime":0},"review"),({"release_date":""},"review"),
 ({"keywords":{"keywords":[{"id":123,"name":"stand-up comedy"}]}},"review"),
 ({"video":True},"review"),({"adult":True},"excluded")])
def test_scope_decisions(changes,status):
    assert classify(MoviePayload.model_validate(movie(**changes)),CUTOFF)["status"]==status

@pytest.mark.parametrize("job,role",[("Director","director"),("Assistant Director",None),("Screenplay","writer"),("Story",None),("Director of Photography","cinematographer"),("Camera Operator",None),("Original Music Composer","composer"),("Music Supervisor",None)])
def test_exact_crew_mapping(job,role):
    c=CreditPayload(id=12,name="Synthetic",job=job)
    assert credit_role("crew",c)[0]==role

@pytest.mark.parametrize("character,role",[("Detective","actor"),("Robot (voice)","actor"),("Self",None),("Himself (archive footage)",None),("Detective (uncredited)",None),("",None)])
def test_cast_eligibility_is_not_known_for_department(character,role):
    c=CreditPayload(id=12,name="Synthetic",character=character,known_for_department="Acting")
    assert credit_role("cast",c)[0]==role

def test_credit_dedup_keeps_multi_role_identity_and_distinct_jobs():
    data=movie();data["credits"]["crew"].append(deepcopy(data["credits"]["crew"][0]))
    rows,duplicates=normalize_credits(MoviePayload.model_validate(data))
    assert duplicates==1 and len(rows)==3
    assert {c["role"] for c in rows if c["person_source_id"]==910002}=={"director","writer"}

def test_conflicting_source_credit_id_is_rejected():
    data=movie();copy=deepcopy(data["credits"]["crew"][0]);copy["job"]="Writer";data["credits"]["crew"].append(copy)
    with pytest.raises(ValueError):normalize_credits(MoviePayload.model_validate(data))

def test_missing_credit_ids_use_stable_composite_keys():
    data=movie()
    for c in data["credits"]["crew"]:c.pop("credit_id")
    rows,_=normalize_credits(MoviePayload.model_validate(data))
    assert all(c["dedupe_key"].startswith("composite:") for c in rows if c["kind"]=="crew")

def test_manual_review_preserves_hard_exclusions_and_requires_runtime_evidence():
    override=ReviewOverride(decision="eligible",reason="Reviewed narrative feature metadata",reviewer="Local reviewer",confirmed_narrative_feature=True,verified_runtime_minutes=90)
    result=classify(MoviePayload.model_validate(movie(runtime=None)),CUTOFF,override)
    assert result["status"]=="eligible" and result["runtime"]==90
    assert classify(MoviePayload.model_validate(movie(genres=[{"id":99,"name":"Documentary"}])),CUTOFF,override)["status"]=="excluded"
    assert classify(MoviePayload.model_validate(movie(release_date="")),CUTOFF,override)["status"]=="review"

def test_image_urls_require_provider_configuration_and_safe_source_path():
    assert image_url(CONFIG["images"],"/fixture-test.jpg","poster")=="https://image.tmdb.org/t/p/w342/fixture-test.jpg"
    for bad in [None,"https://unrelated.example/x.jpg","//unrelated.example/x.jpg","/../x.jpg"]:
        assert image_url(CONFIG["images"],bad,"poster") is None
    bad=deepcopy(CONFIG);bad["images"]["secure_base_url"]="https://unrelated.example/"
    with pytest.raises(ValidationError):ConfigurationPayload.model_validate(bad)

@pytest.mark.parametrize("change",[{"id":True},{"id":-1},{"vote_average":float("nan")},{"credits":{}},{"keywords":{}}])
def test_bad_upstream_values_cannot_be_published(change):
    with pytest.raises(ValidationError):MoviePayload.model_validate(movie(**change))
