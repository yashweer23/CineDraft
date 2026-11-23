"""Versioned scrypt password hashes and opaque eight-hour bearer tokens."""
import hashlib,hmac,re,secrets
PREFIX='acct_'
N=2**15;R=8;P=3  # OWASP scrypt alternative: 32 MiB, p=3.

def username(value):
    name=value.strip().lower()
    if not re.fullmatch(r'[a-z0-9_]{3,32}',name):raise ValueError('Use 3–32 letters, digits or underscores for the public username.')
    return name

def password(value):
    if not 15<=len(value)<=128 or len(value.encode('utf-8'))>512:raise ValueError('Use a password of 15–128 characters, at most 512 UTF-8 bytes.')
    if len(set(value))<4 or value.casefold() in {'passwordpassword','password123456789','123456789012345','qwertyuiopasdfgh','letmeinletmein123'}:raise ValueError('Choose a less predictable passphrase.')
    return value

def derive(value,salt):return hashlib.scrypt(value.encode('utf-8'),salt=salt,n=N,r=R,p=P,maxmem=64*1024*1024,dklen=32)

def hash_password(value):
    password(value);salt=secrets.token_bytes(16)
    return f'scrypt-1${N}${R}${P}${salt.hex()}${derive(value,salt).hex()}'

def verify_password(value,encoded):
    try:
        version,n,r,p,salt,digest=encoded.split('$')
        if (version,int(n),int(r),int(p))!=('scrypt-1',N,R,P) or len(salt)!=32 or len(digest)!=64:return False
        if not 1<=len(value)<=128 or len(value.encode('utf-8'))>512:return False
        return hmac.compare_digest(derive(value,bytes.fromhex(salt)),bytes.fromhex(digest))
    except (ValueError,TypeError,AttributeError):return False

DUMMY=f'scrypt-1${N}${R}${P}$'+('00'*16)+'$'+('00'*32)
def new_token():return PREFIX+secrets.token_urlsafe(32)
def token_hash(value):
    if not re.fullmatch(r'acct_[A-Za-z0-9_-]{43}',value):raise ValueError('Invalid account session.')
    return hashlib.sha256(value.encode('ascii')).hexdigest()
