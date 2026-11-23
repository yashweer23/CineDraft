from uuid import UUID
from fastapi import APIRouter,Request
from app.contracts import MutationRequest,ContractError
from app.drafting.api import Token,call
from app.simulation import service
from app.simulation.schemas import ReleaseReceipt,SavedResult,SimulationStatus

router=APIRouter(prefix='/api/v1/drafts',tags=['Scoring and fictional release simulation'],
    responses={401:{'model':ContractError},404:{'model':ContractError},409:{'model':ContractError},422:{'model':ContractError},503:{'model':ContractError}})

@router.post('/{draft_id}/release',response_model=ReleaseReceipt)
def release(request:Request,draft_id:UUID,body:MutationRequest,token:Token):
    return call(request,service.release,token,draft_id,'release',body)

@router.post('/{draft_id}/retry-simulation',response_model=ReleaseReceipt)
def retry(request:Request,draft_id:UUID,body:MutationRequest,token:Token):
    return call(request,service.release,token,draft_id,'retry_simulation',body)

@router.get('/{draft_id}/simulation',response_model=SimulationStatus)
def status(request:Request,draft_id:UUID,token:Token):return call(request,service.status,token,draft_id)

@router.get('/{draft_id}/result',response_model=SavedResult)
def result(request:Request,draft_id:UUID,token:Token):return call(request,service.result,token,draft_id)
