from dataclasses import replace
from uuid import UUID
import pytest
from app.talent.calculation import Film, Person, Credit
from app.collaboration import calculation as g


def uid(n): return str(UUID(int=n))
def movie(n, **kw): return Film(uid(100+n), 'fixture', f'fixture:film-{n}', f'Synthetic film {n}', **kw)
def credit(pid, mid, role='actor', job='Actor'): return Credit(uid(pid), uid(100+mid), role, job)
def people(*ids): return [Person(uid(n)) for n in ids]


def test_canonical_roles_stay_attached_to_people_when_reversed():
    a=(uid(1),'director'); b=(uid(2),'actor')
    assert g.canonical_pair(*b,*a)==(a,b)
    assert g.edge_key(a,b)==g.edge_key(b,a)
    assert g.edge_key(a,b)!=g.edge_key((uid(1),'actor'),(uid(2),'director'))
    with pytest.raises(ValueError,match='different people'):
        g.canonical_pair(uid(1),'director',uid(1),'actor')


@pytest.mark.parametrize('count,expected',[(0,0),(1,4),(2,8),(3,12),(4,12),(1000,12)])
def test_bonus_caps(count,expected): assert g.bonus(count)==expected


@pytest.mark.parametrize('bad',[-1,1.5,True,'2'])
def test_bonus_rejects_invalid_counts(bad):
    with pytest.raises(ValueError): g.bonus(bad)


def test_multiple_jobs_and_duplicate_credits_count_one_film_with_full_evidence():
    rows=[credit(1,1,'writer','Screenplay'),credit(1,1,'writer','Story'),credit(2,1)]
    graph=g.build_graph([movie(1)],people(1,2),rows+rows)
    edge=graph['edges'][0]
    assert edge['shared_movie_count']==1 and edge['bonus']==4
    assert edge['evidence']==[{'movie_id':uid(101),'jobs_a':['Screenplay','Story'],'jobs_b':['Actor']}]
    assert graph==g.build_graph([movie(1)],people(2,1),list(reversed(rows)))


def test_all_evidence_survives_cap_and_reordering():
    films=[movie(i) for i in range(1,7)]
    rows=[credit(pid,mid) for pid in (1,2) for mid in range(1,7)]
    graph=g.build_graph(films,people(1,2),rows)
    assert graph['edges'][0]['bonus']==12
    assert len(graph['edges'][0]['evidence'])==6
    assert graph['report']['evidence_rows']==6
    assert graph==g.build_graph(list(reversed(films)),people(2,1),list(reversed(rows)))


def test_role_evidence_does_not_leak_across_films_or_people():
    rows=[credit(1,1,'actor'),credit(2,1,'actor'),credit(1,2,'director','Director'),credit(3,2,'composer','Original Music Composer')]
    graph=g.build_graph([movie(1),movie(2)],people(1,2,3),rows)
    lookup={e['edge_id']:e for e in graph['edges']}
    assert g.edge_key((uid(1),'director'),(uid(2),'actor')) not in lookup
    assert g.edge_key((uid(1),'actor'),(uid(3),'composer')) not in lookup
    assert len(graph['nodes'])==4 and len(graph['edges'])==2


def test_excluded_movies_unmapped_jobs_and_self_edges_are_absent():
    rows=[credit(1,1,'director','Director'),credit(1,1,'writer','Story'),credit(2,1,None,'Producer'),credit(1,2),credit(2,2)]
    graph=g.build_graph([movie(1),movie(2,eligible=False)],people(1,2),rows)
    assert len(graph['nodes'])==2 and graph['edges']==[]
    assert graph['report']['isolated_nodes']==2


def test_zero_shared_films_preserves_two_eligible_isolated_nodes():
    graph=g.build_graph([movie(1),movie(2)],people(1,2),[credit(1,1),credit(2,2)])
    assert graph['report']['nodes']==2 and graph['report']['edges']==0
    assert graph['report']['isolated_nodes']==2


def test_jobs_change_hash_even_when_edge_count_unchanged():
    baseline=g.build_graph([movie(1)],people(1,2),[credit(1,1,'writer','Story'),credit(2,1)])
    changed=g.build_graph([movie(1)],people(1,2),[credit(1,1,'writer','Screenplay'),credit(2,1)])
    assert baseline['report']==changed['report']
    assert baseline['input_hash']!=changed['input_hash'] and baseline['output_hash']!=changed['output_hash']


@pytest.mark.parametrize('case',['duplicate_movie','duplicate_person','missing_person','missing_movie','bad_role','empty_job','no_mapped'])
def test_invalid_inputs_fail_before_publication(case):
    films=[movie(1)]; persons=people(1,2); rows=[credit(1,1),credit(2,1)]
    if case=='duplicate_movie': films.append(movie(1))
    elif case=='duplicate_person': persons+=people(1)
    elif case=='missing_person': rows.append(credit(3,1))
    elif case=='missing_movie': rows.append(credit(1,2))
    elif case=='bad_role': rows=[credit(1,1,'producer')]
    elif case=='empty_job': rows=[credit(1,1,job=' ')]
    else: rows=[credit(1,1,None)]
    with pytest.raises(ValueError): g.build_graph(films,persons,rows)


def test_resource_bound_fails_instead_of_publishing_truncated_graph(monkeypatch):
    monkeypatch.setattr(g,'MAX_PAIR_OBSERVATIONS',2)
    with pytest.raises(ValueError,match='no output was published'):
        g.build_graph([movie(1)],people(1,2,3),[credit(i,1) for i in (1,2,3)])
