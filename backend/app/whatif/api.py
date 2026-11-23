from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Request,Query
from app.domain import Slot
from app.drafting.api import Token,call
from app.whatif import service,schemas as w
router=APIRouter(prefix='/api/v1/drafts/{draft_id}/what-if',tags=['Private hypothetical comparisons'])
Limit=Annotated[int,Query(ge=1,le=50)];Offset=Annotated[int,Query(ge=0,le=100000)]
@router.get('/candidates',response_model=w.Candidates)
def candidates(request:Request,token:Token,draft_id:UUID,slot:Slot,limit:Limit=12,offset:Offset=0):return call(request,service.candidates,token,draft_id,slot,limit,offset)
@router.post('',response_model=w.Saved)
def create(request:Request,token:Token,draft_id:UUID,body:w.CompareRequest):return call(request,service.create,token,draft_id,body)
@router.get('',response_model=w.History)
def history(request:Request,token:Token,draft_id:UUID,limit:Limit=10,offset:Offset=0):return call(request,service.history,token,draft_id,limit,offset)
@router.get('/{analysis_id}',response_model=w.Saved)
def read(request:Request,token:Token,draft_id:UUID,analysis_id:UUID):return call(request,service.read,token,draft_id,analysis_id)
