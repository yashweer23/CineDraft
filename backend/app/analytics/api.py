from uuid import UUID
from fastapi import APIRouter,Request
from app.drafting.api import call,Token
from app.drafting.schemas import LiveDraft
from . import service
from .schemas import Stream,ReplayRequest
router=APIRouter(prefix='/api/v1/drafts/{draft_id}',tags=['Owner gameplay analytics'])
@router.get('/analytics-events',response_model=Stream)
def events(request:Request,draft_id:UUID,token:Token):return call(request,service.export,token,draft_id)
@router.post('/replay',response_model=LiveDraft)
def replay(request:Request,draft_id:UUID,body:ReplayRequest,token:Token):return call(request,service.replay,token,draft_id,body)
