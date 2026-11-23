# Phase 6 — graph design and persistence

A node is `(person UUID, professional role)` with at least one eligible mapped film credit in the selected sealed dataset. A person may have several nodes but retains one identity. Isolated nodes are kept. A graph depends on the raw dataset, not on Phase 5 prices or ratings.

An edge joins two nodes whose people differ. Roles stay attached to their people. A writer/actor edge is not interchangeable with an actor/writer edge for the same two people. Canonical order is ascending person UUID; reversing the request produces the same edge and evidence. The edge ID hashes the two ordered `[person_id, role]` endpoints and is scoped by graph ID in storage.

## Evidence and bonus

The builder groups eligible credits by movie and person-role, deduplicates jobs, then enumerates distinct-person node pairs within each movie. Multiple screenplay/story jobs on one film count as one shared film. Evidence retains every exact matching job for both endpoints. Unmapped credits and excluded/review movies do not contribute. Eligibility comes from the frozen import policy and cutoff, not today's clock.

`bonus = min(12, 4 × distinct shared eligible movie count)`.

| Shared films | Bonus |
|---:|---:|
| 0 | 0 |
| 1 | 4 |
| 2 | 8 |
| 3 | 12 |
| 6 | 12, with all six films retained |

Missing edges between valid role nodes return “No shared credits found in this dataset.” Missing/ineligible nodes return 404. Self-pairs return 422. No personal relationship, compatibility or friendship claims are made.

The graph contains all observed role-pair connections. Future chemistry selects the twelve designated roster relationships from the Phase 1 specification and uses `H = 60 + 40 × sum(b)/(12 × 12)`. This phase implements edge bonuses/evidence, not full roster chemistry or simulation. Do not sum every graph edge into a team score.

## Determinism and bounds

Canonical sorting and integer arithmetic make reordered equivalent inputs and duplicate identical jobs produce identical hashes. Changing credited jobs changes evidence and hashes even when the count stays the same. Evidence films sort by UUID; the order is stable, not a subjective ranking.

`collaboration-1.0` pins parameters, role mapping, dataset scope and dataset manifest hash. The graph manifest also records normalized input/full output hashes, source and report. Its canonical hash is the graph hash. Immutable source snapshots bind names, titles and provider identities; output hashes cover node counts, edges and every movie/job evidence row.

The in-memory builder preflights at most 500,000 pair/movie observations. Larger jobs fail before graph inserts. Nothing is silently truncated. Complexity depends on the sum of squared credited role-node counts per movie, plus sorting/output storage. Large casts still increase cost; no large-catalog performance benchmark is claimed.

## Persistence

Migration `0003_phase6` adds four tables:

| Table | Purpose / identity |
|---|---|
| `graph_versions` | Frozen manifest and seal status; graph ID |
| `graph_nodes` | Eligible person-role node and distinct film count; graph/person/role |
| `graph_edges` | Canonical endpoints, shared count and bonus; graph/edge |
| `graph_evidence` | Exact jobs on one source movie; graph/edge/movie |

Composite foreign keys bind nodes and evidence to the correct dataset. Constraints reject self/reversed edges and enforce the bonus. Insert triggers validate node film counts and exact role-specific jobs. The seal trigger checks manifest row counts and per-edge evidence counts. One-way seal and append-only guards prevent updating/deleting published versions, changing members or appending after sealing.

The official builder constructs the complete graph and cryptographic hashes. Database guards enforce structural/source-evidence invariants; they do not cryptographically recompute the full graph.

Publication obtains an advisory transaction lock, computes from sealed data, inserts unsealed metadata and batched members, then seals and commits once. Failures roll back the entire new graph. Identical reruns are no-ops; changed/incomplete output under an existing label fails. Dry-run writes nothing. Historical migrations, old snapshots and Phase 5 versions remain untouched.

Downgrading Phase 6 removes graph tables only. The test suite exercises downgrade in temporary schemas; it is not a user-data troubleshooting procedure. Future schema changes need new migrations.
