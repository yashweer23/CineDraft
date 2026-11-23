"""Small persistence helpers, not the Phase 7 command engine or an auth system."""
import hashlib
import json
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.contracts import FrozenInputs, ResultView
from app.models import Draft, DraftSnapshot, Result, ActionRecord, Pick, DatasetVersion, FeatureVersion, RulesVersion, ScoringVersion

def canonical_hash(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

class IdempotencyConflict(ValueError):
    pass

def replay_action(session: Session, draft_id: UUID, command: str, request_id: UUID, body: dict):
    """Caller must authorize ownership and lock the draft BEFORE calling this."""
    row = session.scalar(select(ActionRecord).where(ActionRecord.draft_id == draft_id, ActionRecord.command == command, ActionRecord.request_id == request_id))
    if row and row.body_hash != canonical_hash(body):
        raise IdempotencyConflict("Request ID was previously used with a different body")
    return row

def save_snapshot(session: Session, inputs: FrozenInputs) -> DraftSnapshot:
    """Caller owns the surrounding transaction. No implicit commits."""
    data = inputs.model_dump(mode="json")
    draft = session.scalar(select(Draft).where(Draft.id == inputs.draft.draft_id).with_for_update())
    if draft is None or draft.revision != inputs.draft.revision or draft.status != inputs.draft.status:
        raise ValueError("Snapshot must match the persisted draft state and revision")
    if draft.talent_spend_usd != inputs.draft.budget.talent_spend_usd or draft.seed != inputs.seed:
        raise ValueError("Snapshot money and seed must match the persisted draft")
    for key in ("dataset_id", "feature_id", "pricing_id", "rules_id", "scoring_id", "prng_version", "simulation_version"):
        if getattr(draft, key) != getattr(inputs.draft.versions, key):
            raise ValueError("Snapshot versions must match the persisted draft")
    if hasattr(inputs.draft.versions, 'graph_id'):
        from app.models import GraphVersion
        graph = session.get(GraphVersion, draft.graph_id)
        if (graph is None or draft.graph_id != inputs.draft.versions.graph_id
                or graph.content_hash != inputs.draft.versions.graph_hash
                or graph.configuration != inputs.graph_configuration):
            raise ValueError("Snapshot graph must match its frozen version")
    stored_picks = session.scalars(select(Pick).where(Pick.draft_id == draft.id)).all()
    actual = {(p.slot, p.person_id, p.offer_id, p.locked_fee_usd) for p in stored_picks}
    expected = {(p.slot.value, p.person_id, p.offer_id, p.locked_fee_usd) for p in inputs.draft.picks}
    if actual != expected:
        raise ValueError("Snapshot roster must match all persisted picks")
    for key in ("tier", "total_budget_usd", "reserve_usd", "talent_budget_usd"):
        if getattr(draft, key) != getattr(inputs.draft.budget, key):
            raise ValueError("Snapshot allocation must match persisted draft")
    if draft.genre_id != inputs.draft.genre_id:
        raise ValueError("Snapshot genre must match persisted draft")
    if session.get(DatasetVersion, draft.dataset_id).role_mapping_version != inputs.draft.versions.role_mapping_version or session.get(FeatureVersion, draft.feature_id).ranking_version != inputs.draft.versions.ranking_version:
        raise ValueError("Snapshot mapping and ranking versions must match")
    if session.get(RulesVersion, draft.rules_id).configuration != inputs.rules_configuration or session.get(ScoringVersion, draft.scoring_id).configuration != inputs.scoring_configuration:
        raise ValueError("Snapshot configurations must match sealed versions")
    row = DraftSnapshot(draft_id=draft.id, revision=draft.revision, input_hash=canonical_hash(data), inputs=data)
    session.add(row)
    session.flush()
    return row

def load_snapshot(session: Session, draft_id: UUID) -> FrozenInputs:
    row = session.get(DraftSnapshot, draft_id)
    if row is None:
        raise LookupError("Snapshot not found")
    if row.input_hash != canonical_hash(row.inputs):
        raise ValueError("Snapshot integrity check failed")
    if row.inputs.get('schema_version') == 'phase7-v1':
        from app.drafting.schemas import FrozenDraft
        return FrozenDraft.model_validate(row.inputs)
    return FrozenInputs.model_validate(row.inputs)

def save_result(session: Session, value: ResultView) -> Result:
    snapshot = session.get(DraftSnapshot, value.draft_id)
    if snapshot is None or snapshot.input_hash != value.input_hash:
        raise ValueError("Result must reference the exact frozen input hash")
    frozen = load_snapshot(session, value.draft_id)
    if value.simulation_version != frozen.draft.versions.simulation_version or value.synthetic != frozen.synthetic:
        raise ValueError("Result version and source marker must match frozen inputs")
    data = value.model_dump(mode="json")
    row = Result(draft_id=value.draft_id, input_hash=value.input_hash, simulation_id=value.simulation_id, simulation_version=value.simulation_version, output_hash=canonical_hash(data), outputs=data)
    session.add(row)
    session.flush()
    return row
