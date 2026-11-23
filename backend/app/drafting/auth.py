"""Random guest capabilities. Store SHA-256 digests only, with expiry/revocation."""
from datetime import datetime,timedelta,timezone
import hashlib,re,secrets
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import models as m
from app.drafting.errors import DraftProblem


def token_hash(token):
    if len(token)==48 and token.startswith('acct_'):
        from app.accounts.security import token_hash as account_hash
        try:return account_hash(token)
        except ValueError:raise DraftProblem(401,'invalid_session','A valid bearer token is required.') from None
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        raise DraftProblem(401,'invalid_session','A valid, unexpired guest bearer token is required.')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def authorize(s,token,*,exclusive=False):
    if len(token)==48 and token.startswith('acct_'):
        from app.accounts.service import authorize as account_authorize
        return account_authorize(s,token,exclusive=exclusive)
    digest=token_hash(token)
    query=select(m.GuestSession).where(m.GuestSession.token_hash==digest,m.GuestSession.revoked_at.is_(None),m.GuestSession.expires_at>func.now())
    row=s.scalar(query.with_for_update(read=not exclusive))
    if row is None:raise DraftProblem(401,'invalid_session','A valid, unexpired guest bearer token is required.')
    if s.get(m.AccountOwnership,row.id) is not None:raise DraftProblem(401,'guest_claimed','This guest session was moved to an account. Sign in instead.')
    return row


def create_session(engine):
    token=secrets.token_urlsafe(32);expires=datetime.now(timezone.utc)+timedelta(days=30)
    with Session(engine) as s,s.begin():
        s.add(m.GuestSession(token_hash=token_hash(token),expires_at=expires))
    return {'access_token':token,'token_type':'bearer','expires_at':expires}


def revoke_session(engine,token):
    if len(token)==48 and token.startswith('acct_'):raise DraftProblem(422,'use_account_logout','Use the account logout endpoint.')
    with Session(engine) as s,s.begin():
        owner=authorize(s,token,exclusive=True);owner.revoked_at=datetime.now(timezone.utc)
    return {'revoked':True}
