from dataclasses import replace
from datetime import date
from decimal import Decimal as D, localcontext
import random
import pytest
from app.talent.calculation import (Film, Person, Credit, build_features, build_prices,
    percentiles, adjusted_reception, price_profile, round_fee, FEATURE_VERSION, LIMITS)
from app.repository import canonical_hash

def film(key, **values):
    return Film(id=key, source="fixture", source_key="fixture:"+key, title="Synthetic "+key,
        **({"rating": D(7), "votes": 1000, "release_date": date(2020,1,1), "genres": frozenset({"drama"})} | values))

def one(films=None, people=None, credits=None):
    films = films or [film("f1")]
    return build_features(films, people or [Person("p1")], credits or [Credit("p1", f.id, "director", "Director") for f in films])

def test_low_vote_outlier_is_shrunk_below_supported_film():
    a=film("outlier",rating=D("9.9"),votes=2); b=film("supported",rating=D(8),votes=5000)
    assert adjusted_reception(a,D("6.5")) == D("3269.8") / 502
    assert adjusted_reception(a,D("6.5")) < adjusted_reception(b,D("6.5"))
    assert one([a,b])["profiles"][0]["evidence"]["notable_works"][0]["movie_id"]=="supported"

def test_catalog_prior_is_unweighted_mean_and_excludes_noneligible():
    result=one([film("a",rating=D(4),votes=1),film("b",rating=D(8),votes=99999),film("c",rating=D(10),eligible=False)])
    assert D(result["report"]["catalog_rating_prior"])==6
    assert result["profiles"][0]["attributes"]["coverage"]["eligible_movies"]==2

@pytest.mark.parametrize("rating,votes",[(None,None),(D(9),0),(None,500),(D(9),None)])
def test_missing_reception_keeps_prior_internal_and_flags_evidence(rating,votes):
    p=one([film("a",rating=rating,votes=votes,poster_path=None,release_date=None)])["profiles"][0]
    assert p["attributes"]["reception"]==60
    assert p["attributes"]["coverage"]["reception_prior_only"]
    assert p["attributes"]["popularity_percentile"] is None
    assert p["attributes"]["appeal_popularity"]==50 and p["attributes"]["pricing_popularity"]==0
    w=p["evidence"]["notable_works"][0]
    assert not w["reception_available"] and w["effective_votes"]==0
    assert p["attributes"]["career_span_years"] is None

def test_exact_role_and_duplicate_movie_credits():
    credits=[Credit("p","a","director","Director"),Credit("p","a","writer","Writer"),
             Credit("p","a","writer","Screenplay"),Credit("p","a","writer","Writer"),Credit("p","b","actor","Actor")]
    profiles=build_features([film("a"),film("b")],[Person("p")],credits)["profiles"]
    writer=next(p for p in profiles if p["role"]=="writer")
    assert writer["attributes"]["coverage"]["eligible_movies"]==1
    assert writer["evidence"]["notable_works"][0]["credited_jobs"]==["Screenplay","Writer"]
    director=next(p for p in profiles if p["role"]=="director")
    assert [w["movie_id"] for w in director["evidence"]["notable_works"]]==["a"]
    assert len({p["person_id"] for p in profiles})==1

def test_genre_prior_uses_distinct_person_movie_pairs_and_reports_gaps():
    films=[film("a"),film("b",genres=frozenset({"action"}))]
    credits=[Credit("p","a","writer","Writer"),Credit("p","a","writer","Screenplay"),Credit("q","a","writer","Writer"),Credit("p","b","writer","Writer")]
    profiles=build_features(films,[Person("p"),Person("q")],credits)["profiles"]
    p=next(p for p in profiles if p["person_id"]=="p")
    assert abs(D(p["evidence"]["genre_priors"]["drama"])-D(2)/3)<D("1e-27")
    assert p["evidence"]["genre_counts"]["drama"]==1
    assert "horror" in p["evidence"]["genre_catalog_gaps"]
    assert D(p["evidence"]["genre_priors"]["horror"])==D("0.5")
    assert "horror" not in p["attributes"]["specialties"]

def test_percentiles_ties_singleton_and_missing():
    assert percentiles({"a":D(1),"b":D(1),"c":D(4),"d":None})=={"a":D(".25"),"b":D(".25"),"c":D(1)}
    assert percentiles({"a":D(99),"b":None})=={"a":D(".5")}
    assert percentiles({"a":None})=={}

def test_popularity_is_ranked_within_role_and_cannot_change_strength():
    people=[Person("p",D(10)),Person("q",D(100)),Person("r",D(1000))]
    credits=[Credit("p","a","director","Director"),Credit("q","a","director","Director"),Credit("r","a","actor","Actor")]
    rows=build_features([film("a")],people,credits)["profiles"]
    p=next(x for x in rows if x["person_id"]=="p");q=next(x for x in rows if x["person_id"]=="q")
    assert p["attributes"]["popularity_percentile"]==0 and q["attributes"]["popularity_percentile"]==100
    assert p["attributes"]["talent_strength"]==q["attributes"]["talent_strength"]
    assert price_profile("director",p["attributes"])["fee_usd"]<price_profile("director",q["attributes"])["fee_usd"]

def test_ranking_top_five_is_deduplicated_stable_and_numeric_id_ties():
    # Pure numeric ordering example only, not claimed to be real source observations or persisted.
    films=[replace(film(str(i)),source="tmdb",source_key=str(i)) for i in [20,2,11,3,10,9,1]]
    works=one(films)["profiles"][0]["evidence"]["notable_works"]
    assert [w["movie_id"] for w in works]==["1","2","3","9","10"]
    assert [w["rank"] for w in works]==[1,2,3,4,5]

def test_short_filmography_has_no_filler_and_never_uses_excluded_movie():
    assert len(one([film("a"),film("b",eligible=False,rating=D(10))])["profiles"][0]["evidence"]["notable_works"])==1

def test_output_and_hash_ignore_input_order_and_duplicate_jobs():
    films=[film("a"),film("b",rating=D(9)),film("c",rating=None)]
    people=[Person("p"),Person("q",D(40))]
    credits=[Credit(p.id,f.id,"writer","Writer") for p in people for f in films]
    first=build_features(films,people,credits)
    random.Random(7).shuffle(credits)
    second=build_features(list(reversed(films)),list(reversed(people)),credits+[credits[0]])
    assert canonical_hash(first)==canonical_hash(second)
    assert build_prices(first["profiles"])==build_prices(second["profiles"])

def test_decimal_context_is_isolated():
    expected=one()
    with localcontext() as ctx:
        ctx.prec=7
        assert one()==expected

@pytest.mark.parametrize("n,level",[(1,"low"),(2,"low"),(3,"moderate"),(7,"moderate"),(8,"broader"),(30,"broader"),(40,"broader")])
def test_coverage_thresholds_and_experience_cap(n,level):
    p=one([film(str(i)) for i in range(n)])["profiles"][0]
    assert p["attributes"]["coverage"]["level"]==level
    assert 0<=p["attributes"]["experience"]<=100
    if n>=30:assert p["attributes"]["experience"]==100

@pytest.mark.parametrize("role",list(LIMITS))
def test_prices_at_endpoints_and_exact_integer_money(role):
    def attr(v):return {"schema_version":FEATURE_VERSION,"talent_strength":v,"pricing_popularity":v,"experience":v}
    assert price_profile(role,attr(0))["fee_usd"]==LIMITS[role][0]
    assert price_profile(role,attr(100))["fee_usd"]==LIMITS[role][1]
    fee=price_profile(role,attr(50))["fee_usd"]
    assert type(fee) is int and fee%25000==0
    assert LIMITS[role][0]<=fee<=LIMITS[role][1]

def test_half_up_rounding_and_clamp():
    assert round_fee(D(112500),100000,30000000)==125000
    assert round_fee(D("112499.999"),100000,30000000)==100000
    assert round_fee(D(1),100000,30000000)==100000
    assert round_fee(D(40000000),100000,30000000)==30000000

def test_sparse_actor_pool_cannot_enable_a_tier():
    report=build_prices(one()["profiles"])["report"]
    assert "actor" in report["missing_roster_roles"]
    assert report["optimistic_roster_lower_bound_usd"] is None
    assert all(not t["enabled"] for t in report["tiers"].values())

def test_optimistic_lower_bound_is_not_a_feasibility_certificate():
    a={"schema_version":FEATURE_VERSION,"talent_strength":0,"pricing_popularity":0,"experience":0}
    profiles=[{"person_id":"same", "role":r,"attributes":a} for r in LIMITS if r!="actor"]
    profiles += [{"person_id":"actor"+str(i),"role":"actor","attributes":a} for i in range(4)]
    report=build_prices(profiles)["report"]
    assert report["optimistic_roster_lower_bound_usd"]==850000
    assert report["tiers"]["indie"]["diagnostic"]=="needs_exact_assignment_check"
    assert all(not t["enabled"] for t in report["tiers"].values())

def test_empty_roles_and_malformed_numeric_observations_fail():
    with pytest.raises(ValueError,match="No eligible"):build_features([film("a")],[Person("p")],[Credit("p","a",None,"Story")])
    with pytest.raises(ValueError,match="rating"):one([film("a",rating=D("NaN"))])
    with pytest.raises(ValueError,match="Duplicate"):one([film("a"),film("a")])
