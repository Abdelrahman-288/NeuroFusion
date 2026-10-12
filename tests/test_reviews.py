import json
import pytest
from neurofusion.jobs import JobStore


class Predictor:
    def analyze(self, path, task, output):
        output.mkdir(parents=True)
        (output / 'result.json').write_text(json.dumps({'task': task, 'views': [{}, {}]}))


def completed(root):
    store = JobStore(root, Predictor())
    job = store.submit(b'image', 'tumor-image', 'image.png', '.png')['id']
    store.run_one()
    return store, job


def payload(**extra):
    return dict(reviewer='QA reviewer', note='Test observation, not a medical finding.',
                assessment='uncertain', slice_index=0, **extra)


def test_review_history_persists_without_changing_predictions(tmp_path, monkeypatch):
    store, job = completed(tmp_path)
    monkeypatch.setattr('neurofusion.jobs.now', lambda: '2026-10-06T00:00:00+00:00')
    path = tmp_path / 'results' / job / 'result.json'
    before = path.read_bytes()
    first = store.add_review(job, payload())
    second = dict(payload(), note='Correction to the earlier test note.', slice_index=None)
    store.add_review(job, second)
    reopened = JobStore(tmp_path, Predictor()).reviews(job)
    assert len(reopened['reviews']) == 2
    assert reopened['reviews'][0] == first
    assert reopened['reviewer_identity_verified'] is False
    assert path.read_bytes() == before
    assert len(first['result_sha256']) == 64


@pytest.mark.parametrize('field,value', [('reviewer',''), ('reviewer','x'*81), ('note',' '),
    ('note','x'*4001), ('assessment','diagnosed'), ('slice_index',-1), ('slice_index',2),
    ('slice_index',True), ('slice_index',0.5), ('note',[]), ('reviewer',None)])
def test_invalid_reviews_not_saved(tmp_path, field, value):
    store, job = completed(tmp_path)
    data = payload(); data[field] = value
    with pytest.raises(ValueError): store.add_review(job, data)
    assert store.reviews(job)['reviews'] == []


def test_review_requires_completed_job_and_stays_with_its_job(tmp_path):
    store, job = completed(tmp_path)
    queued = store.submit(b'image', 'tumor-image', 'other.png', '.png')['id']
    with pytest.raises(ValueError): store.add_review(queued, payload())
    with pytest.raises(ValueError): store.reviews('../unknown')
    store.add_review(job, payload())
    store.run_one()
    assert store.reviews(queued)['reviews'] == []
