"""Real password crypto and opaque sessions, with no database substitute."""
import hashlib
import pytest
from pydantic import ValidationError
from app.accounts import security,schemas as w
from app.drafting import auth
GOOD='a long private passphrase!'

def test_random_salts_exact_unicode_password_and_no_plaintext():
    pw='  A long 密码 passphrase!  ';a=security.hash_password(pw);b=security.hash_password(pw)
    assert a!=b and pw not in a and security.verify_password(pw,a)
    assert not security.verify_password(pw.strip(),a) and not security.verify_password(pw+'X',a)
    assert not security.verify_password(GOOD,security.DUMMY)

@pytest.mark.parametrize('value',['short','a'*16,'passwordpassword','password123456789','a'*129])
def test_weak_or_unbounded_passwords(value):
    with pytest.raises(ValueError):security.hash_password(value)
    with pytest.raises(ValidationError):w.Registration(username='public_name',password=value)

@pytest.mark.parametrize('encoded',['',None,'scrypt-1$1048576$8$3$'+'00'*16+'$'+'00'*32,'scrypt-1$32768$8$3$'+'zz'*16+'$'+'00'*32])
def test_corrupt_or_expensive_parameters_fail_closed(encoded):
    assert not security.verify_password(GOOD,encoded)

@pytest.mark.parametrize('value',['a','x'*33,'hello.world','sai ya','../name','你好世界'])
def test_public_username_shape(value):
    with pytest.raises(ValueError):security.username(value)

def test_normalization_secrets_and_extra_fields():
    reg=w.Registration(username='  Studio_Name  ',password=GOOD)
    assert reg.username=='studio_name' and GOOD not in repr(reg) and GOOD not in reg.model_dump_json()
    with pytest.raises(ValidationError):w.Registration(username='studio',password=GOOD,admin=True)
    with pytest.raises(ValidationError):w.Claim(guest_token='acct_'+'a'*43)

def test_token_namespaces():
    token=security.new_token();assert token!=security.new_token() and token.startswith('acct_') and len(token)==48
    assert auth.token_hash(token)==security.token_hash(token)==hashlib.sha256(token.encode()).hexdigest()
    assert auth.token_hash('g'*43)==hashlib.sha256(('g'*43).encode()).hexdigest()
    guest='acct_'+'g'*38
    assert auth.token_hash(guest)==hashlib.sha256(guest.encode()).hexdigest()
    for value in ('acct_'+'a'*42,'acct_'+'!'*43,'a'*43):
        with pytest.raises(ValueError):security.token_hash(value)
