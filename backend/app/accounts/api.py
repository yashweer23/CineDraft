from fastapi import APIRouter,Request
from app.accounts import schemas as w,service
from app.drafting.api import Token
from app.drafting.errors import DraftProblem
from sqlalchemy.exc import SQLAlchemyError
router=APIRouter(prefix='/api/v1/accounts',tags=['Local accounts'])

def call(request,operation,*args):
    try:return operation(request.app.state.database.engine,*args)
    except SQLAlchemyError:raise DraftProblem(503,'account_operation_unavailable','Account operation could not be confirmed. Sign in to check registration or password-change outcomes; repeat the same guest proof for a claim.') from None

def ip(request):return request.client.host if request.client else 'unknown'
@router.post('/register',response_model=w.SignedIn,status_code=201)
def register(request:Request,body:w.Registration):return call(request,service.register,body,ip(request))
@router.post('/login',response_model=w.SignedIn)
def login(request:Request,body:w.Credentials):return call(request,service.login,body,ip(request))
@router.get('/me',response_model=w.AccountView)
def me(request:Request,token:Token):return call(request,service.me,token)
@router.post('/logout',response_model=w.SignedOut)
def logout(request:Request,token:Token):return call(request,service.logout,token)
@router.post('/claim-guest',response_model=w.Claimed)
def claim(request:Request,token:Token,body:w.Claim):return call(request,service.claim_guest,token,body)
@router.post('/password',response_model=w.ChangedPassword)
def change_password(request:Request,token:Token,body:w.PasswordChange):return call(request,service.change_password,token,body)
