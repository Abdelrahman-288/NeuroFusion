"""Explicit-file, hashed local release bundles and fresh-directory recovery."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import zipfile

def checksum(data):return hashlib.sha256(data).hexdigest()

def safe_name(name):
    p=PurePosixPath(name)
    if not isinstance(name,str) or not name or '\\' in name or ':' in name or p.is_absolute() or any(part in ('','..','.') or part.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',part) for part in name.split('/')):
        raise ValueError('Unsafe archive path')
    return name

def build_bundle(files,destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('Fresh archive path required')
    normalized={};seen=set()
    for name,path in files.items():
        safe_name(name)
        if name.lower() in seen or name.lower()=='bundle-manifest.json':raise ValueError('Duplicate or reserved name')
        seen.add(name.lower());path=Path(path)
        if not path.is_file() or path.is_symlink():raise ValueError('Regular files required')
        normalized[name]=path
    destination.parent.mkdir(parents=True,exist_ok=True)
    records=[]
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(normalized.items()):
            data=path.read_bytes();records.append({'path':name,'sha256':checksum(data),'bytes':len(data)});archive.writestr(name,data)
        archive.writestr('bundle-manifest.json',json.dumps({'schema_version':1,'research_only':True,'files':records},indent=2))
    return verify_bundle(destination)

def verify_bundle(path):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(n.lower() for n in names)):raise ValueError('Duplicate archive members')
        for member in archive.infolist():
            safe_name(member.filename)
            if member.is_dir() or (member.external_attr>>16)&0o170000==0o120000:raise ValueError('Directories and symlinks are not allowed')
        if sum(m.file_size for m in archive.infolist())>1024**3:raise ValueError('Bundle exceeds 1 GiB')
        document=json.loads(archive.read('bundle-manifest.json'));rows=document['files']
        if len(rows)!=len({r['path'].lower() for r in rows}) or set(names)!={'bundle-manifest.json',*(r['path'] for r in rows)}:raise ValueError('Manifest inventory mismatch')
        for row in rows:
            data=archive.read(row['path'])
            if len(data)!=row['bytes'] or checksum(data)!=row['sha256']:raise ValueError('Bundle checksum mismatch')
    return {'passed':True,'files':len(rows),'sha256':checksum(Path(path).read_bytes()),'bytes':Path(path).stat().st_size}

def restore_bundle(path,destination):
    result=verify_bundle(path);destination=Path(destination)
    if destination.exists():raise ValueError('Recovery requires a new destination; existing files are never replaced')
    destination.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as handle:handle.write(archive.read(name))
    return result
