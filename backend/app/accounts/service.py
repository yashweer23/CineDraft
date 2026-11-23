from dataclasses import dataclass
from datetime import timedelta
import hashlib,secrets
from sqlalchemy import select,func,update,tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.accounts import security
from app.drafting.errors import DraftProblem

@dataclass(frozen=True)
class Principal:
    account_id:object
    username:str
    id:object  # Stable internal guest owner for new account films.
    token_hash:str
    account_session_id:object


def now(s):return s.scalar(select(func.clock_timestamp()))
def view(a):return dict(account_id=a.id,username=a.username)
def invalid():return DraftProblem(401,'invalid_account_session','Sign in with a valid account session.')

def authorize(s,token,*,exclusive=False):
    try:digest=security.token_hash(token)
    except ValueError:raise invalid() from None
    # Read identity first, then lock account -> session consistently for password/logout races.
    account_id=s.scalar(select(m.AccountSession.account_id).where(m.AccountSession.token_hash==digest))
    a=s.scalar(select(m.Account).where(m.Account.id==account_id).with_for_update(read=not exclusive)) if account_id else None
    if a is None:raise invalid()
    session=s.scalar(select(m.AccountSession).where(m.AccountSession.token_hash==digest,m.AccountSession.revoked_at.is_(None),m.AccountSession.expires_at>func.clock_timestamp()).with_for_update(read=True))
    if session is None:raise invalid()
    guest=s.get(m.GuestSession,a.primary_guest_id)
    return Principal(a.id,a.username,guest.id,guest.token_hash,session.id)

def ownership_scope(owner):
    if isinstance(owner,Principal):
        owners=select(m.GuestSession.id,m.GuestSession.token_hash).join(m.AccountOwnership,m.AccountOwnership.guest_session_id==m.GuestSession.id).where(m.AccountOwnership.account_id==owner.account_id)
        return tuple_(m.DraftRuntime.session_id,m.Draft.owner_key_hash).in_(owners)
    return (m.DraftRuntime.session_id==owner.id)&(m.Draft.owner_key_hash==owner.token_hash)

def reserve_auth_attempt(engine,username,ip,*,registration=False):
    # Two independent bounded sliding windows. Raw addresses/handles are not persisted here.
    namespace='register' if registration else 'login'
    keys=[(namespace+':ip:'+hashlib.sha256(ip.encode()).hexdigest(),5 if registration else 30,3600 if registration else 900)]
    if not registration:keys.append(('login:user:'+hashlib.sha256(username.encode()).hexdigest(),10,900))
    limited=False
    with Session(engine) as s,s.begin():
        timestamp=now(s).timestamp();rows=[]
        for key,limit,seconds in sorted(keys):
            s.execute(insert(m.AuthThrottle).values(bucket=key,events=[]).on_conflict_do_nothing(index_elements=['bucket']))
            row=s.scalar(select(m.AuthThrottle).where(m.AuthThrottle.bucket==key).with_for_update())
            events=[t for t in row.events if t>timestamp-seconds]
            rows.append((row,events));limited|=len(events)>=limit
        if not limited:
            for row,events in rows:row.events=events+[timestamp]
    if limited:raise DraftProblem(429,'authentication_throttled','Too many authentication attempts. Wait for the sliding window to clear.')

def signed_in(s,a):
    token=security.new_token();expires=now(s)+timedelta(hours=8)
    s.add(m.AccountSession(account_id=a.id,token_hash=security.token_hash(token),expires_at=expires));s.flush()
    return dict(access_token=token,token_type='bearer',expires_at=expires,account=view(a))

def register(engine,body,ip):
    reserve_auth_attempt(engine,body.username,ip,registration=True)
    encoded=security.hash_password(body.password.get_secret_value())
    try:
        with Session(engine) as s,s.begin():
            # No usable guest credential exists for this internal historical owner key.
            time=now(s);g=m.GuestSession(token_hash=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),expires_at=time+timedelta(days=30),revoked_at=time)
            s.add(g);s.flush();a=m.Account(username=body.username,password_hash=encoded,primary_guest_id=g.id);s.add(a);s.flush()
            s.add(m.AccountOwnership(guest_session_id=g.id,account_id=a.id));s.flush()
            return signed_in(s,a)
    except IntegrityError:raise DraftProblem(409,'account_unavailable','This public username cannot be registered. Choose another or sign in.') from None

def login(engine,body,ip):
    reserve_auth_attempt(engine,body.username,ip)
    with Session(engine) as s,s.begin():
        a=s.scalar(select(m.Account).where(m.Account.username==body.username).with_for_update(read=True))
        valid=security.verify_password(body.password.get_secret_value(),a.password_hash if a else security.DUMMY)
        if not a or not valid:raise DraftProblem(401,'invalid_credentials','Invalid username or password.')
        return signed_in(s,a)

def me(engine,token):
    with Session(engine) as s,s.begin():
        a=authorize(s,token);return dict(account_id=a.account_id,username=a.username)

def logout(engine,token):
    with Session(engine) as s,s.begin():
        a=authorize(s,token,exclusive=True);s.get(m.AccountSession,a.account_session_id).revoked_at=now(s)
    return {'signed_out':True}

def claim_guest(engine,token,body):
    guest_digest=hashlib.sha256(body.guest_token.get_secret_value().encode('ascii')).hexdigest()
    with Session(engine) as s,s.begin():
        a=authorize(s,token,exclusive=True)
        g=s.scalar(select(m.GuestSession).where(m.GuestSession.token_hash==guest_digest).with_for_update())
        if g is None:raise DraftProblem(401,'invalid_guest_proof','A valid, unexpired guest recovery token is required.')
        existing=s.get(m.AccountOwnership,g.id)
        if existing:
            if existing.account_id!=a.account_id:raise DraftProblem(409,'guest_already_claimed','This guest session has already been claimed.')
        else:
            time=now(s)
            if g.revoked_at is not None or g.expires_at<=time:raise DraftProblem(401,'invalid_guest_proof','A valid, unexpired guest recovery token is required.')
            s.add(m.AccountOwnership(guest_session_id=g.id,account_id=a.account_id));g.revoked_at=time;s.flush()
        count=s.scalar(select(func.count()).select_from(m.DraftRuntime).where(m.DraftRuntime.session_id==g.id))
        return {'claimed':True,'films':count,'guest_access_revoked':True}

def change_password(engine,token,body):
    with Session(engine) as s,s.begin():
        principal=authorize(s,token,exclusive=True);a=s.get(m.Account,principal.account_id)
        if not security.verify_password(body.current_password.get_secret_value(),a.password_hash):raise DraftProblem(401,'invalid_credentials','Current password is incorrect.')
        a.password_hash=security.hash_password(body.new_password.get_secret_value())
        s.execute(update(m.AccountSession).where(m.AccountSession.account_id==a.id,m.AccountSession.revoked_at.is_(None)).values(revoked_at=now(s)))
    return {'password_changed':True,'all_sessions_revoked':True}

def reset_password(engine,name,new_password):
    encoded=security.hash_password(new_password)
    with Session(engine) as s,s.begin():
        a=s.scalar(select(m.Account).where(m.Account.username==security.username(name)).with_for_update())
        if a is None:raise ValueError('Account not found.')
        a.password_hash=encoded;s.execute(update(m.AccountSession).where(m.AccountSession.account_id==a.id,m.AccountSession.revoked_at.is_(None)).values(revoked_at=now(s)))
    return {'reset':True,'all_sessions_revoked':True}
