import sqlite3
import pytest
from neurofusion.release_operations import backup_private,restore_private,database_check


def test_private_backup_recovery_and_no_overwrite(tmp_path):
    source=tmp_path/'private';source.mkdir()
    with sqlite3.connect(source/'jobs.sqlite3') as c:
        c.execute('CREATE TABLE notes(value TEXT)');c.execute("INSERT INTO notes VALUES('private note')")
    (source/'scan.bin').write_bytes(b'private image')
    a=backup_private(source,tmp_path/'backup.zip');b=restore_private(tmp_path/'backup.zip',tmp_path/'recovered')
    assert a['databases']==b['databases']=={'jobs.sqlite3':{'notes':1}}
    assert (tmp_path/'recovered/scan.bin').read_bytes()==b'private image'
    with pytest.raises(ValueError):restore_private(tmp_path/'backup.zip',source)
    with pytest.raises(ValueError):backup_private(source,source/'backup.zip')


def test_active_journal_and_corrupt_database_rejected(tmp_path):
    source=tmp_path/'private';source.mkdir();(source/'jobs.sqlite3-wal').write_bytes(b'active')
    with pytest.raises(ValueError,match='journal'):backup_private(source,tmp_path/'backup.zip')
    (tmp_path/'bad.db').write_bytes(b'corrupt')
    with pytest.raises(sqlite3.DatabaseError):database_check(tmp_path/'bad.db')


def test_monitor_detects_missing_results_failed_jobs_and_checkpoint_damage(tmp_path,monkeypatch):
    from neurofusion.release_operations import monitor_local
    from neurofusion.cohort import digest
    import neurofusion.model_registry as registry
    model=tmp_path/'model.pt';model.write_bytes(b'model')
    expected=digest(model)
    monkeypatch.setattr(registry,'active_models',lambda *args:{'test':('model.pt',expected)})
    storage=tmp_path/'private';storage.mkdir()
    with sqlite3.connect(storage/'jobs.sqlite3') as c:
        c.execute('CREATE TABLE jobs(id TEXT,status TEXT)')
        c.execute("INSERT INTO jobs VALUES('abc','completed')")
    assert not monitor_local(tmp_path,storage,0)['checks']['completed_results_present']
    result=storage/'results/abc/result.json';result.parent.mkdir(parents=True);result.write_text('{}')
    assert monitor_local(tmp_path,storage,0)['healthy']
    with sqlite3.connect(storage/'jobs.sqlite3') as c:c.execute("INSERT INTO jobs VALUES('def','failed')")
    assert not monitor_local(tmp_path,storage,0)['checks']['no_failed_or_interrupted_jobs']
    model.write_bytes(b'changed')
    assert not monitor_local(tmp_path,storage,0)['checks']['model_integrity']
