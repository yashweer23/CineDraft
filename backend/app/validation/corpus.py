"""Versioned, invented inputs for engineering experiments; never a live catalog."""
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5
from app.domain import GENRES, TIERS, Role, Slot, SLOT_ROLES
from app.repository import canonical_hash
from app.drafting.assignment import Talent, validate_pool, legal_candidates
from app.drafting.rules import choose_offer, RELATIONSHIPS
from app.drafting.schemas import FrozenDraft
from app.simulation.example import synthetic_snapshot
from app.simulation.engine import simulate
from app.simulation.schemas import SimulationResult
from app.talent.calculation import FEATURE_VERSION, price_profile
from app.collaboration.calculation import canonical_pair, edge_key, NO_SHARED

VERSION = 'validation-corpus-1.0'
STRATEGIES = ('random', 'genre_greedy', 'star_heavy')

def identity(key):
    return str(uuid5(NAMESPACE_URL, 'cinedraft:' + VERSION + ':' + key))

def number(*parts):
    return int(canonical_hash([VERSION, *parts])[:16], 16)

def catalog():
    profiles = {}; groups = {}
    for role in Role:
        for j in range(20):
            # Four shared identities across all five roles deliberately exercise
            # the unique-person constraint. Every role also has cheap specialists.
            pid = identity(f'shared:{j}' if j % 5 == 0 else f'{role}:{j}')
            strength = min(100, 8 + 4*j + number(role, j, 'strength') % 13)
            popularity = min(20, j*5) if j < 4 else number(pid, 'popularity') % 101
            attributes = dict(schema_version=FEATURE_VERSION, talent_strength=strength,
                popularity_percentile=popularity, pricing_popularity=popularity, experience=j*5,
                genre_fit={g: number(role, j, g) % 101 for g in GENRES},
                coverage={'level':'broader', 'eligible_movies':10, 'synthetic':True})
            profiles[pid, role.value] = dict(person_id=pid, role=role.value, attributes=attributes,
                evidence={'synthetic':True, 'genre_catalog_gaps':[]})
            groups[pid] = j % 7
    pool = [Talent(pid, role, price_profile(role, p['attributes'])['fee_usd']) for (pid, role), p in profiles.items()]
    validate_pool(pool)
    return pool, profiles, groups

def draft(seed, genre, tier, strategy, *, reverse_pool=False):
    if strategy not in STRATEGIES or genre not in GENRES or tier not in TIERS:
        raise ValueError('Unknown experiment cell')
    pool, profiles, groups = catalog()
    if reverse_pool: pool.reverse()
    envelope = TIERS[tier]*65//100; available = envelope; used = set(); chosen = []; trace = []
    for revision, slot in enumerate(Slot):
        rows = legal_candidates(pool, slot, list(Slot)[revision+1:], used, available)
        offered = choose_offer(rows, seed, f'pick:{slot.value}:{revision}')
        legal = [r['talent'] for r in offered if r['selectable']]
        if not legal: raise ValueError('Synthetic corpus cannot complete this brief')
        def key(t):
            attrs = profiles[t.person_id, t.role]['attributes']
            value = (number(seed, slot.value, t.person_id, 'strategy') if strategy == 'random'
                else attrs['genre_fit'][genre] if strategy == 'genre_greedy' else attrs['popularity_percentile'])
            return (-value, t.person_id)
        pick = min(legal, key=key)
        trace.append({'slot':slot.value, 'offered':[r['talent'].person_id for r in offered],
            'selectable':[r['talent'].person_id for r in offered if r['selectable']], 'selected':pick.person_id,
            'fee_usd':pick.fee_usd, 'remaining_usd':available-pick.fee_usd})
        chosen.append(pick); used.add(pick.person_id); available -= pick.fee_usd
    spend = envelope-available
    frozen = synthetic_snapshot(seed=seed, tier=tier, spend=spend).model_dump(mode='json')
    graph = {'synthetic':True, 'version':VERSION, 'rule':'same j modulo 7: 1 + group modulo 3 shared fictional films'}
    fingerprint = canonical_hash(sorted((pid, role, p) for (pid, role), p in profiles.items()))
    versions = frozen['draft']['versions']
    versions.update(dataset_id='fixture:phase13', feature_id='features:phase13', pricing_id='pricing:phase13',
        graph_id='graph:phase13', catalog_id='draft-catalog:phase13', graph_hash=canonical_hash(graph),
        catalog_hash=canonical_hash([fingerprint, graph]), feature_hash=fingerprint,
        pricing_hash=canonical_hash(sorted((t.person_id,t.role,t.fee_usd) for t in pool)))
    frozen['graph_configuration'] = graph
    frozen['draft'].update(draft_id=identity(f'{seed}:{genre}:{tier}'), genre_id=genre)
    for i, (slot, t) in enumerate(zip(Slot, chosen)):
        profile = deepcopy(profiles[t.person_id,t.role]); attrs = profile['attributes']
        frozen['draft']['picks'][i].update(person_id=t.person_id, locked_fee_usd=t.fee_usd,
            offer_id=identity(f'{seed}:pick:{slot.value}:{i}'))
        frozen['cards'][i].update(person_id=t.person_id, hiring_fee_usd=t.fee_usd, name=f'Synthetic {t.person_id[:8]}',
            talent_strength=attrs['talent_strength'], genre_fit=attrs['genre_fit'][genre], versions=deepcopy(versions))
        frozen['role_features'][i] = profile
    roster = {slot.value:t.person_id for slot,t in zip(Slot,chosen)}
    for edge, (a,b) in zip(frozen['collaborations'], RELATIONSHIPS):
        left,right = canonical_pair(roster[a], SLOT_ROLES[Slot(a)], roster[b], SLOT_ROLES[Slot(b)])
        group = groups[roster[a]]; count = 1+group%3 if group == groups[roster[b]] else 0
        edge.update(canonical_a=list(left), canonical_b=list(right), shared_movie_count=count, bonus=4*count,
            edge_id=edge_key(left,right) if count else None, message='Synthetic shared evidence.' if count else NO_SHARED,
            evidence=[dict(movie_id=identity(f'group:{group}:film:{j}'), jobs_a=['Synthetic credit'], jobs_b=['Synthetic credit']) for j in range(count)])
    model = FrozenDraft.model_validate(frozen); input_hash = canonical_hash(model.model_dump(mode='json'))
    result = SimulationResult.model_validate(simulate(model,input_hash)).model_dump(mode='json')
    # Validate actual engine accounting and exact replay, not rounded-score equality.
    assert len(used) == 8 and 0 <= spend <= envelope
    assert result == SimulationResult.model_validate(simulate(model,input_hash)).model_dump(mode='json')
    return model, result, trace
