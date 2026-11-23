"""A release is one atomic command; CPU work is bounded and requires no queue."""
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.repository import canonical_hash,load_snapshot,save_result
from app.drafting import service as drafts
from app.drafting.auth import authorize
from app.drafting.errors import DraftProblem
from app.simulation.engine import simulate,verify_snapshot,SimulationInputError,MANIFEST_HASH,SIMULATION_VERSION
from app.simulation.schemas import SimulationResult,AttemptView,ReleaseReceipt,SavedResult

logger=logging.getLogger('cinedraft')


def latest(s,draft_id):
    return s.scalar(select(m.SimulationAttempt).where(m.SimulationAttempt.draft_id==draft_id).order_by(m.SimulationAttempt.attempt_number.desc()).limit(1))


def attempt_view(row):
    if row is None:return None
    return AttemptView(attempt_id=row.id,attempt_number=row.attempt_number,command=row.command,request_id=row.request_id,
        revision=row.revision,status=row.status,error_code=row.error_code,created_at=row.created_at,
        message='Release result saved.' if row.status=='succeeded' else 'Simulation could not complete. Retry uses the same frozen inputs and seed.').model_dump(mode='json')


def status(engine,token,draft_id):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=drafts.owned(s,owner,draft_id)
        return dict(draft_id=d.id,status=d.status,latest_attempt=attempt_view(latest(s,d.id)),result_available=s.get(m.Result,d.id) is not None)


def result(engine,token,draft_id):
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=drafts.owned(s,owner,draft_id)
        from app.challenges.service import guard_result
        guard_result(s,d.id)
        row=s.get(m.Result,d.id)
        if row is None:raise DraftProblem(404,'result_not_available','No release result has been saved for this draft.')
        if row.output_hash!=canonical_hash(row.outputs):raise DraftProblem(503,'result_integrity_error','Saved result integrity check failed. Existing data was preserved.')
        try:value=SimulationResult.model_validate(row.outputs)
        except ValueError:raise DraftProblem(503,'result_integrity_error','Saved result schema validation failed. Existing data was preserved.') from None
        if value.input_hash!=row.input_hash or value.simulation_id!=row.simulation_id or value.draft_id!=d.id:
            raise DraftProblem(503,'result_integrity_error','Saved result identity check failed. Existing data was preserved.')
        return SavedResult(output_hash=row.output_hash,result=value).model_dump(mode='json')


def release(engine,token,draft_id,command,body):
    data=body.model_dump(mode='json');digest=canonical_hash(data)
    with Session(engine) as s,s.begin():
        owner=authorize(s,token);d,rt,c=drafts.owned(s,owner,draft_id,write=True)
        prior=s.scalar(select(m.ActionRecord).where(m.ActionRecord.draft_id==d.id,m.ActionRecord.command==command,m.ActionRecord.request_id==body.request_id))
        if prior:
            if prior.body_hash!=digest:raise DraftProblem(409,'idempotency_conflict','Request ID was used with a different body.',d.revision)
            return prior.response_body
        if body.expected_revision!=d.revision:raise DraftProblem(409,'stale_revision','Draft changed. Refresh before choosing a new action.',d.revision)
        from app.challenges.service import guard_action,finish
        guard_action(s,d.id,command)
        expected={'release':'production_finalized','retry_simulation':'simulation_failed'}.get(command)
        if expected is None or d.status!=expected:raise DraftProblem(409,'invalid_release_state','Release requires finalized inputs; retry requires a failed simulation.',d.revision)
        if s.get(m.Result,d.id) is not None:raise DraftProblem(409,'result_exists','This film already has an immutable result.',d.revision)
        try:
            snapshot=s.get(m.DraftSnapshot,d.id)
            if snapshot is None:raise SimulationInputError('Finalized inputs are missing.')
            frozen=load_snapshot(s,d.id);verify_snapshot(frozen,snapshot.input_hash)
        except (ValueError,LookupError) as error:
            # Input rejection is not a committed simulation attempt.
            message=str(error) if isinstance(error,SimulationInputError) else 'Frozen input integrity or schema validation failed.'
            raise DraftProblem(422,'unsupported_simulation_input',message,d.revision) from None
        previous=latest(s,d.id);number=previous.attempt_number+1 if previous else 1
        before=d.revision;d.status='simulation_running';s.flush()
        try:
            value=SimulationResult.model_validate(simulate(frozen,snapshot.input_hash))
        except SimulationInputError as error:
            raise DraftProblem(422,'unsupported_simulation_input',str(error),before) from None
        except Exception as error:
            # Do not persist exception messages, credentials or stack locals.
            logger.error('Simulation engine failure: draft_id=%s command_id=%s error_type=%s',d.id,body.request_id,type(error).__name__)
            value=None
        # SQL failures below propagate and roll back state, result, attempt and receipt.
        output_hash=None
        if value is not None:output_hash=save_result(s,value).output_hash
        d.status='results_available' if value is not None else 'simulation_failed';d.revision+=1;s.flush()
        attempt=m.SimulationAttempt(draft_id=d.id,input_hash=snapshot.input_hash,attempt_number=number,command=command,
            request_id=body.request_id,revision=d.revision,simulation_version=SIMULATION_VERSION,engine_manifest_hash=MANIFEST_HASH,
            status='succeeded' if value is not None else 'failed',error_code=None if value is not None else 'engine_error',output_hash=output_hash)
        s.add(attempt);s.flush()
        if value is not None:finish(s,d.id,value,output_hash)
        response=ReleaseReceipt(draft=drafts.view(s,d,rt,c),attempt=attempt_view(attempt)).model_dump(mode='json')
        s.add(m.ActionRecord(draft_id=d.id,command=command,request_id=body.request_id,body_hash=digest,request_body=data,
            response_body=response,response_status=200,revision_before=before,revision_after=d.revision));s.flush()
        return response
