from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError
from app import contracts as c
from app.drafting import schemas as w,service,auth,catalog
from app.drafting.errors import DraftProblem

router=APIRouter(prefix='/api/v1',tags=['Authoritative classic drafting'],
    responses={401:{'model':c.ContractError},404:{'model':c.ContractError},409:{'model':c.ContractError},422:{'model':c.ContractError},503:{'model':c.ContractError}})
bearer=HTTPBearer(auto_error=False,description='Server-issued guest or account bearer session. Never use the draft UUID as a token.')

def bearer_token(credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer)]):
    if credentials is None or credentials.scheme.lower()!='bearer':raise DraftProblem(401,'invalid_session','Create a guest session or sign in to your account first.')
    auth.token_hash(credentials.credentials)
    return credentials.credentials

Token=Annotated[str,Depends(bearer_token)]

def call(request,operation,*args,**kwargs):
    try:return operation(request.app.state.database.engine,*args,**kwargs)
    except SQLAlchemyError:raise DraftProblem(503,'database_unavailable','Database operation could not complete. Refresh and retry with the SAME request ID and body; check the migration and API logs.') from None

@router.post('/sessions',response_model=w.SessionCreated,status_code=201)
def new_session(request:Request):return call(request,auth.create_session)

@router.post('/sessions/revoke',response_model=w.SessionRevoked)
def revoke(request:Request,token:Token):return call(request,auth.revoke_session,token)

@router.get('/catalog',response_model=w.CatalogAvailability)
def active_catalog(request:Request):return call(request,catalog.availability)

@router.post('/drafts',response_model=w.LiveDraft,status_code=201)
def create(request:Request,body:c.CreateDraftRequest,token:Token):return call(request,service.create,token,body)

@router.get('/drafts',response_model=w.DraftPage)
def drafts(request:Request,token:Token,limit:Annotated[int,Query(ge=1,le=20)]=5,offset:Annotated[int,Query(ge=0,le=100000)]=0):
    return call(request,service.list_drafts,token,limit,offset)

@router.get('/drafts/{draft_id}',response_model=w.LiveDraft)
def read(request:Request,draft_id:UUID,token:Token):return call(request,service.read,token,draft_id)

@router.get('/drafts/{draft_id}/roster',response_model=w.RosterView)
def roster(request:Request,draft_id:UUID,token:Token):return call(request,service.roster,token,draft_id)


def register(path,command,model):
    def endpoint(request:Request,draft_id:UUID,body,token:Token):
        return call(request,service.mutate,token,draft_id,command,body)
    endpoint.__name__=command
    endpoint.__annotations__['body']=model
    router.add_api_route('/drafts/{draft_id}/'+path,endpoint,methods=['POST'],response_model=w.LiveDraft)

for path,command,model in [
    ('picks','pick',c.PickRequest),('rerolls','reroll',c.RerollRequest),
    ('recast/preview','preview_recast',c.RecastPreviewRequest),('recast/cancel','cancel_recast',c.RecastCancelRequest),
    ('recast/confirm','confirm_recast',c.RecastConfirmRequest),('finalize','finalize',c.MutationRequest),('abandon','abandon',c.MutationRequest),
]:register(path,command,model)
