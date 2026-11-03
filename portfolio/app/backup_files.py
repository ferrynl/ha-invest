"""Inventory of application-owned backup/update files; never traverse links."""
import hashlib
import os
from pathlib import Path, PurePosixPath

ROOTS=('backups','updates')

def file_path(store,name):
    if not isinstance(name,str) or '\\' in name or '\x00' in name:raise ValueError('Ongeldig back-upbestand.')
    parts=PurePosixPath(name).parts
    if len(parts)<2 or parts[0] not in ROOTS or any(p in ('','.','..') for p in parts) or PurePosixPath(name).is_absolute():raise ValueError('Ongeldig back-upbestand.')
    root=store.root.resolve();path=root
    for part in parts:
        path=path/part
        if path.is_symlink() or path.is_junction():raise ValueError('Ongeldig back-upbestand.')
    if not path.is_file() or not path.resolve().is_relative_to(root/parts[0]):raise ValueError('Back-upbestand niet gevonden.')
    return path

def revision(path):
    stat=path.stat()
    return hashlib.sha256(f'{stat.st_dev}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}'.encode()).hexdigest()

def inventory(store):
    files=[]
    for category in ROOTS:
        root=store.root/category
        if root.is_symlink() or root.is_junction() or not root.is_dir():continue
        for folder,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if not (Path(folder)/d).is_symlink() and not (Path(folder)/d).is_junction()]
            for name in names:
                path=Path(folder)/name
                if path.is_symlink() or not path.is_file():continue
                try:
                    stat=path.stat();identity=path.relative_to(store.root).as_posix()
                    with path.open('rb') as stream:restorable=stream.read(16)==b'SQLite format 3\x00'
                    files.append(dict(name=identity,bytes=stat.st_size,modified=stat.st_mtime,revision=revision(path),restorable=restorable,kind='update' if category=='updates' else 'migration' if identity.startswith('backups/migrations/') else 'restore' if identity.startswith('backups/restores/') else 'deletion' if identity.startswith('backups/deletions/') else 'conversion' if identity.startswith('backups/conversions/') else 'backup'))
                except OSError:continue
    files.sort(key=lambda row:(row['modified'],row['name']),reverse=True)
    return dict(files=files,total_bytes=sum(row['bytes'] for row in files),backup_bytes=sum(row['bytes'] for row in files if row['kind']!='update'),update_bytes=sum(row['bytes'] for row in files if row['kind']=='update'))

def reviewed_file(store,data):
    path=file_path(store,data.get('name'))
    if not isinstance(data.get('revision'),str) or data['revision']!=revision(path):raise ValueError('Het bestand is gewijzigd. Vernieuw het overzicht.')
    return path
