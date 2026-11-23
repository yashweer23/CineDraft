"""Build/verify an allowlisted source ZIP with SHA-256 hashes. Python standard library only."""
import argparse,hashlib,json,re,stat,sys,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
PREFIX='CineDraft-VSCode/'
MAX_FILES=2000
MAX_FILE=20*1024*1024
MAX_TOTAL=100*1024*1024
EXCLUDED={'node_modules','.git','.venv','venv','__pycache__','.pytest_cache','.browser-tools','test-results',
    'playwright-report','dist','build','coverage','analytics-output','validation-output','release-output','backups','.cache'}
DENIED_SUFFIXES=('.pyc','.log','.tsbuildinfo','.local.json','.sqlite','.sqlite-wal','.sqlite-shm','.sqlite-journal','.db','.dump','.backup','.pem','.key','.zip')


def digest(value):return hashlib.sha256(value).hexdigest()

def safe_name(name):
    p=PurePosixPath(name)
    if not p.parts or any(ord(ch)<32 for ch in name) or '\\' in name or ':' in name or p.is_absolute() or str(p)!=name or any(part in ('..','.') for part in p.parts):
        raise ValueError('Invalid release path')
    if any(part in EXCLUDED for part in p.parts) or any(part.startswith('.env') and part!='.env.example' for part in p.parts):
        raise ValueError('Private/generated path cannot enter a source release')
    if name.endswith(DENIED_SUFFIXES) or re.fullmatch(r'gameplay-[0-9a-f]{12}\.json',p.name):
        raise ValueError('Private/generated file cannot enter a source release')
    return p


def source_files(root):
    root=Path(root).resolve();listing=root/'release-files.txt'
    if listing.is_symlink():raise ValueError('Symlinked allowlist refused')
    names=[line.strip() for line in listing.read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len(names)!=len(set(names)) or not 1<=len(names)<=MAX_FILES or 'MANIFEST.sha256' in names:raise ValueError('Invalid or duplicate allowlist entry')
    if 'release-files.txt' not in names:raise ValueError('Allowlist must include itself')
    values={};total=0
    for name in sorted(names):
        relative=safe_name(name);path=root
        for part in relative.parts:
            path=path/part
            if path.is_symlink():raise ValueError('Symlinked source refused: '+name)
        if not path.is_file():raise ValueError('Allowlisted source missing: '+name)
        if path.stat().st_size>MAX_FILE:raise ValueError('Source file exceeds size limit')
        value=path.read_bytes();total+=len(value)
        if total>MAX_TOTAL:raise ValueError('Source release exceeds size limit')
        values[name]=value
    return values


def create(root,out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Output exists; choose a new filename')
    values=source_files(root)
    if out in [Path(root).resolve()/n for n in values]:raise ValueError('Output cannot replace a source')
    manifest=''.join(digest(value)+'  '+name+'\n' for name,value in sorted(values.items())).encode('utf-8')
    values['MANIFEST.sha256']=manifest;out.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive final creation avoids replacing a file created while packaging.
    try:
        with out.open('xb') as file,zipfile.ZipFile(file,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,value in sorted(values.items()):
                info=zipfile.ZipInfo(PREFIX+name,date_time=(2026,1,1,0,0,0));info.create_system=3
                info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,value,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    except FileExistsError:
        raise ValueError('Output appeared during packaging; left untouched') from None
    except BaseException:
        if out.exists():out.unlink()
        raise
    return verify(out)


def verify(path):
    path=Path(path)
    if path.stat().st_size>MAX_TOTAL+2*MAX_FILE:raise ValueError('Archive file exceeds size limit')
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist();names=[x.filename for x in infos]
        if len(names)!=len(set(names)) or not 2<=len(names)<=MAX_FILES+1:raise ValueError('Duplicate or invalid archive member count')
        if sum(i.file_size for i in infos)>MAX_TOTAL+MAX_FILE or any(i.file_size>MAX_FILE for i in infos):raise ValueError('Archive exceeds extraction limits')
        for info in infos:
            if not info.filename.startswith(PREFIX) or info.is_dir() or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Invalid archive root or member type')
            safe_name(info.filename[len(PREFIX):])
        manifest=archive.read(PREFIX+'MANIFEST.sha256').decode('utf-8');expected={}
        for line in manifest.splitlines():
            match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
            if not match:raise ValueError('Malformed manifest')
            checksum,name=match.groups();safe_name(name)
            if name in expected or name=='MANIFEST.sha256':raise ValueError('Duplicate manifest entry')
            expected[name]=checksum
        if set(names)!={PREFIX+n for n in expected}|{PREFIX+'MANIFEST.sha256'}:raise ValueError('Manifest and archive differ')
        for name,checksum in expected.items():
            if digest(archive.read(PREFIX+name))!=checksum:raise ValueError('Checksum mismatch: '+name)
        listed=[l.strip() for l in archive.read(PREFIX+'release-files.txt').decode('utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')]
        if len(listed)!=len(set(listed)) or set(listed)!=set(expected):raise ValueError('Allowlist and manifest differ')
    return dict(verified=True,files=len(infos),bytes=path.stat().st_size,sha256=digest(path.read_bytes()),zip=str(path))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    make=sub.add_parser('build');make.add_argument('--out',type=Path)
    check=sub.add_parser('verify');check.add_argument('zip',type=Path);a=p.parse_args(argv)
    try:
        if a.command=='verify':result=verify(a.zip)
        else:
            version=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
            result=create(ROOT,a.out or ROOT/'release-output'/f'CineDraft-v{version}.zip')
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,UnicodeError,zipfile.BadZipFile) as e:
        print('Release check failed: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
