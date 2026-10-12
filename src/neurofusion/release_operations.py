"""Local backup and monitoring checks; no network upload or automatic repair."""
import json,sqlite3,shutil
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.release_bundle import build_bundle,restore_bundle


def database_check(path):
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True) as connection:
        result=connection.execute('PRAGMA integrity_check').fetchall()
        if result!=[('ok',)]:raise ValueError('Database integrity check failed')
        tables=[r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {t:connection.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}


def backup_private(source,archive):
    source=Path(source).resolve();archive=Path(archive).resolve()
    if archive.is_relative_to(source):raise ValueError('Backup must be outside live storage')
    files={p.relative_to(source).as_posix():p for p in source.rglob('*') if p.is_file()}
    if not files:raise ValueError('No private files')
    if any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Private storage must not contain links')
    # A file-copy snapshot requires quiescent writers. No writer is stopped here.
    if any(n.endswith(('-wal','-journal')) for n in files):raise ValueError('Database journal present; quiesce writers and checkpoint before backup')
    before={n:digest(p) for n,p in files.items()}
    databases={n:database_check(p) for n,p in files.items() if p.suffix in ('.db','.sqlite','.sqlite3')}
    result=build_bundle(files,archive)
    after={p.relative_to(source).as_posix():digest(p) for p in source.rglob('*') if p.is_file()}
    if before!=after:raise ValueError('Storage changed during backup; archive is not an accepted snapshot')
    return dict(**result,databases=databases,source_files=len(files),encrypted=False,
        scope='Private local application state only; excludes source datasets and model artifacts outside storage')


def restore_private(archive,destination):
    result=restore_bundle(archive,destination);root=Path(destination)
    result['databases']={p.relative_to(root).as_posix():database_check(p) for p in root.rglob('*') if p.suffix in ('.db','.sqlite','.sqlite3')}
    return result


def monitor_local(project,storage,min_free_bytes=1024**3):
    from neurofusion.inference import MODELS
    from neurofusion.model_registry import active_models
    project=Path(project);storage=Path(storage);checks={};details={}
    free=shutil.disk_usage(project).free;checks['disk_space']=free>=min_free_bytes;details['free_bytes']=free
    try:
        models=active_models(project,MODELS)
        checks['model_integrity']=all(digest(project/p)==sha for p,sha in models.values())
    except (ValueError,OSError,KeyError):checks['model_integrity']=False
    database=storage/'jobs.sqlite3'
    checks['job_database_exists']=database.is_file()
    if database.is_file():
        try:
            database_check(database);checks['database_integrity']=True
            with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as conn:
                states=dict(conn.execute('SELECT status,count(*) FROM jobs GROUP BY status').fetchall())
                missing=0
                for identity, in conn.execute("SELECT id FROM jobs WHERE status='completed'"):
                    path=storage/'results'/identity/'result.json'
                    if not path.is_file():missing+=1
                    else:
                        try:json.loads(path.read_text())
                        except (ValueError,OSError):missing+=1
            details.update(job_counts=states,missing_completed_results=missing)
            checks['completed_results_present']=missing==0
            checks['no_failed_or_interrupted_jobs']=not any(states.get(k,0) for k in ('failed','interrupted'))
        except (ValueError,sqlite3.Error):checks['database_integrity']=False
    return dict(healthy=all(checks.values()),checks=checks,details=details,
        clinical_readiness=False,scope='Local disk, database, result presence and model integrity; not model-quality certification or continuous monitoring')
