import json
import threading
from neurofusion.jobs import JobStore
import pytest


class Predictor:
    def analyze(self, path, task, output):
        if path.read_bytes() == b'bad':
            raise ValueError('invalid input')
        output.mkdir(parents=True)
        (output / 'result.json').write_text(json.dumps({'task': task}))


def test_history_survives_restart_and_queued_work_resumes(tmp_path):
    store = JobStore(tmp_path, Predictor())
    first = store.submit(b'good', 'tumor-image', '../../scan.png', '.png')
    second = store.submit(b'good', 'tumor-image', 'later.png', '.png')
    assert first['filename'] == 'scan.png'
    assert store.run_one()
    restarted = JobStore(tmp_path, Predictor())
    assert restarted.get(first['id'])['status'] == 'completed'
    assert restarted.get(second['id'])['status'] == 'queued'
    assert restarted.run_one()
    assert len(restarted.history()) == 2
    assert not restarted.run_one()


def test_failure_does_not_block_next_job(tmp_path):
    store = JobStore(tmp_path, Predictor())
    failed = store.submit(b'bad', 'tumor-image', 'bad.png', '.png')
    good = store.submit(b'good', 'tumor-image', 'good.png', '.png')
    store.run_one(); store.run_one()
    assert store.get(failed['id'])['status'] == 'failed'
    assert store.get(good['id'])['status'] == 'completed'


def test_interrupted_jobs_are_not_silently_retried(tmp_path):
    store = JobStore(tmp_path, Predictor())
    job = store.submit(b'good', 'tumor-image', 'scan.png', '.png')
    with store.connect() as conn:
        conn.execute("UPDATE jobs SET status='running' WHERE id=?", (job['id'],))
    restarted = JobStore(tmp_path, Predictor())
    assert restarted.get(job['id'])['status'] == 'interrupted'
    assert not restarted.run_one()


def test_queue_limit(tmp_path):
    store = JobStore(tmp_path, Predictor())
    for _ in range(10):
        store.submit(b'good', 'tumor-image', 'scan.png', '.png')
    with pytest.raises(ValueError, match='Queue is full'):
        store.submit(b'good', 'tumor-image', 'scan.png', '.png')
    assert len(list((tmp_path / 'uploads').iterdir())) == 10


def test_legacy_history_import_is_idempotent(tmp_path):
    folder = tmp_path / 'results' / ('a' * 32)
    folder.mkdir(parents=True)
    (folder / 'result.json').write_text('{"task":"stroke-dwi"}')
    JobStore(tmp_path, Predictor())
    store = JobStore(tmp_path, Predictor())
    assert len(store.history()) == 1
    assert store.get('a' * 32)['status'] == 'completed'


def test_background_worker_returns_before_inference_completes(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class Slow(Predictor):
        def analyze(self, *args):
            entered.set()
            assert release.wait(5)
            return super().analyze(*args)
    store = JobStore(tmp_path, Slow())
    store.start()
    try:
        job = store.submit(b'good', 'tumor-image', 'scan.png', '.png')
        assert entered.wait(5)
        assert store.get(job['id'])['status'] == 'running'
        other = store.submit(b'good', 'tumor-image', 'next.png', '.png')
        assert other['status'] == 'queued'
    finally:
        release.set()
        store.close()
    assert store.get(job['id'])['status'] == 'completed'
