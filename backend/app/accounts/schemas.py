from datetime import datetime
from uuid import UUID
from pydantic import SecretStr,field_validator
from app.contracts import Contract
from app.accounts import security

class Credentials(Contract):
    username:str
    password:SecretStr
    @field_validator('username')
    @classmethod
    def name(cls,v):return security.username(v)
    @field_validator('password')
    @classmethod
    def bounded(cls,v):
        raw=v.get_secret_value()
        if not 1<=len(raw)<=128 or len(raw.encode('utf-8'))>512:raise ValueError('Password length is invalid.')
        return v

class Registration(Credentials):
    @field_validator('password')
    @classmethod
    def policy(cls,v):security.password(v.get_secret_value());return v

class AccountView(Contract):
    account_id:UUID
    username:str

class SignedIn(Contract):
    access_token:str
    token_type:str='bearer'
    expires_at:datetime
    account:AccountView

class Claim(Contract):
    guest_token:SecretStr
    @field_validator('guest_token')
    @classmethod
    def shape(cls,v):
        import re
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',v.get_secret_value()):raise ValueError('Invalid guest token.')
        return v

class PasswordChange(Contract):
    current_password:SecretStr
    new_password:SecretStr
    @field_validator('current_password')
    @classmethod
    def bounded(cls,v):
        if not 1<=len(v.get_secret_value())<=128:raise ValueError('Invalid password length.')
        return v
    @field_validator('new_password')
    @classmethod
    def policy(cls,v):security.password(v.get_secret_value());return v

class SignedOut(Contract):
    signed_out:bool
class Claimed(Contract):
    claimed:bool
    films:int
    guest_access_revoked:bool
class ChangedPassword(Contract):
    password_changed:bool
    all_sessions_revoked:bool
