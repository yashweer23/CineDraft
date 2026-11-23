from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Request,Query
from app.challenges import service,schemas as w
from app.drafting.api import Token,call
from app.drafting.schemas import LiveDraft
router=APIRouter(prefix='/api/v1',tags=['Daily challenges and rankings'])
Limit=Annotated[int,Query(ge=1,le=50)];Offset=Annotated[int,Query(ge=0,le=100000)]
@router.get('/challenges',response_model=w.ChallengePage)
def challenges(request:Request,limit:Limit=20,offset:Offset=0):return call(request,service.listing,limit,offset)
@router.get('/challenges/{challenge_id}',response_model=w.ChallengeView)
def challenge(request:Request,challenge_id:str):return call(request,service.detail,challenge_id)
@router.post('/challenges/{challenge_id}/attempts',response_model=LiveDraft,status_code=201)
def begin(request:Request,token:Token,challenge_id:str,body:w.Begin):return call(request,service.begin,token,challenge_id,body)
@router.get('/challenges/{challenge_id}/mine',response_model=w.Mine)
def mine(request:Request,token:Token,challenge_id:str):return call(request,service.mine,token,challenge_id)
@router.get('/challenges/{challenge_id}/leaderboard',response_model=w.Leaderboard)
def leaderboard(request:Request,challenge_id:str,limit:Limit=20,offset:Offset=0):return call(request,service.leaderboard,challenge_id,limit,offset)
@router.get('/challenges/{challenge_id}/audit',response_model=w.Audit)
def audit(request:Request,challenge_id:str):return call(request,service.audit,challenge_id)
@router.get('/drafts/{draft_id}/challenge',response_model=w.Context)
def context(request:Request,token:Token,draft_id:UUID):return call(request,service.context,token,draft_id)
