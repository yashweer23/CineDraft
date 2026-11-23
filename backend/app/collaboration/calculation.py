"""Deterministic role-specific graph; pure calculation, no I/O or current clock."""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
from uuid import UUID
from app.domain import Role
from app.repository import canonical_hash

ALGORITHM_VERSION = "collaboration-1.0"
MAX_PAIR_OBSERVATIONS = 500_000
PARAMETERS = {
    "schema_version": ALGORITHM_VERSION,
    "points_per_shared_movie": 4, "edge_bonus_cap": 12,
    "eligibility": "frozen dataset movie eligibility and mapped professional role",
    "deduplication": "one movie per unordered distinct-person role pair; exact jobs retained",
    "canonical_order": "person UUID ascending; roles stay attached to their person",
    "evidence_order": "movie UUID ascending; jobs sorted by Unicode code point",
    "max_pair_observations": MAX_PAIR_OBSERVATIONS,
}
NO_SHARED = "No shared credits found in this dataset."


def canonical_pair(person_a, role_a, person_b, role_b):
    a = (str(UUID(str(person_a))), Role(role_a).value)
    b = (str(UUID(str(person_b))), Role(role_b).value)
    if a[0] == b[0]:
        raise ValueError("Select two different people; a person cannot collaborate with themselves.")
    return tuple(sorted((a, b)))


def edge_key(a, b):
    left, right = canonical_pair(*a, *b)
    return canonical_hash([list(left), list(right)])


def bonus(shared_movie_count):
    if type(shared_movie_count) is not int or shared_movie_count < 0:
        raise ValueError("Shared-film count must be a non-negative integer")
    return min(12, 4 * shared_movie_count)


def build_graph(films, people, credits):
    # IDs are internal UUIDs, never names or provider numeric IDs.
    mids = [str(UUID(f.id)) for f in films]
    pids = [str(UUID(p.id)) for p in people]
    if len(set(mids)) != len(mids) or len(set(pids)) != len(pids):
        raise ValueError("Duplicate input identity")
    eligible = {str(UUID(f.id)) for f in films if f.eligible}
    all_movies, all_people = set(mids), set(pids)
    jobs = defaultdict(lambda: defaultdict(set))
    for credit in credits:
        pid, mid = str(UUID(credit.person_id)), str(UUID(credit.movie_id))
        if pid not in all_people or mid not in all_movies:
            raise ValueError("Credit references missing source snapshot")
        if credit.role is not None and credit.role not in Role:
            raise ValueError("Unknown mapped professional role")
        if mid in eligible and credit.role is not None:
            if not isinstance(credit.job, str) or not credit.job.strip():
                raise ValueError("Mapped credit needs its source job")
            jobs[mid][(pid, str(credit.role))].add(credit.job)
    counts = Counter(node for members in jobs.values() for node in members)
    if not counts:
        raise ValueError("No eligible mapped role credits in the sealed dataset")
    # Count before allocating edges. Never silently truncate a large graph.
    observations = 0
    for members in jobs.values():
        by_person = Counter(pid for pid, _ in members)
        observations += len(members) * (len(members) - 1) // 2
        observations -= sum(n * (n - 1) // 2 for n in by_person.values())
    if observations > MAX_PAIR_OBSERVATIONS:
        raise ValueError(f"Graph exceeds the {MAX_PAIR_OBSERVATIONS:,} pair/movie observation limit. Build a smaller sealed dataset; no output was published.")
    grouped = defaultdict(list)
    normalized = []
    for mid in sorted(jobs):
        members = jobs[mid]
        for (pid, role), values in sorted(members.items()):
            normalized.append([mid, pid, role, sorted(values)])
        for a, b in combinations(sorted(members), 2):
            if a[0] == b[0]:
                continue
            grouped[(a, b)].append({"movie_id": mid, "jobs_a": sorted(members[a]), "jobs_b": sorted(members[b])})
    nodes = [{"person_id": pid, "role": role, "film_count": n} for (pid, role), n in sorted(counts.items())]
    edges = []
    degree = Counter()
    for (a, b), evidence in sorted(grouped.items()):
        degree[a] += 1; degree[b] += 1
        edges.append({"edge_id": edge_key(a, b), "person_a": a[0], "role_a": a[1],
            "person_b": b[0], "role_b": b[1], "shared_movie_count": len(evidence),
            "bonus": bonus(len(evidence)), "evidence": evidence})
    report = {"eligible_movies": len(eligible), "credited_movies": len(jobs),
        "people": len({pid for pid, _ in counts}), "nodes": len(nodes), "edges": len(edges),
        "evidence_rows": observations, "isolated_nodes": sum(not degree[n] for n in counts),
        "capped_edges": sum(e["shared_movie_count"] >= 3 for e in edges),
        "max_shared_movies": max((e["shared_movie_count"] for e in edges), default=0),
        "nodes_by_role": {r.value: sum(role == r for _, role in counts) for r in Role}}
    return {"nodes": nodes, "edges": edges, "parameters": deepcopy(PARAMETERS), "report": report,
        "input_hash": canonical_hash({"eligible_movies": sorted(eligible), "credits": normalized}),
        "output_hash": canonical_hash({"nodes": nodes, "edges": edges})}
