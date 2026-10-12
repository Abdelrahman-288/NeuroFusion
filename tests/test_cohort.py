import json
import numpy as np
import pytest
from neurofusion.cohort import StudyStore, digest, epoch_order
from neurofusion.data import build_manifest,save_json,split_patients
from neurofusion.demo import create_demo


@pytest.fixture
def store(tmp_path):
    raw=tmp_path/'raw'
    index=create_demo(raw)
    manifest=build_manifest(index,raw,'synthetic')
    mp=tmp_path/'manifest.json'
    save_json(mp,manifest)
    split=split_patients(manifest)
    split.update(frozen=True,manifest_sha256=digest(mp))
    sp=tmp_path/'split.json'
    save_json(sp,split)
    return StudyStore(mp,sp,tmp_path/'cache')


def test_disk_cache_and_no_holdout(store):
    study=store.studies('train')[0]
    x,y,meta=store.load(study)
    assert isinstance(x,np.memmap) and isinstance(y,np.memmap)
    assert x.shape==y.shape
    assert meta['dwi_sha256']==study['files']['dwi']['sha256']
    with pytest.raises(ValueError,match='holdout'):
        store.studies('holdout')
    held=next(s for s in store.manifest['studies'] if store.splits['assignments'][s['subject_id']]=='holdout')
    with pytest.raises(ValueError,match='allowed'):
        store.load(held)


def test_cache_corruption_rejected(store):
    study=store.studies('train')[0]
    folder=store.prepare(study)
    (folder/'image.npy').write_bytes(b'bad')
    store.verified.clear()
    with pytest.raises(ValueError,match='Corrupted'):
        store.load(study)


def test_changed_source_rejected(store):
    study=store.studies('train')[0]
    (store.root/study['files']['dwi']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='Raw source changed'):
        store.load(study)


def test_manifest_binding(store):
    mp=store.manifest_path
    mp.write_text(mp.read_text()+' ')
    with pytest.raises(ValueError,match='manifest hash'):
        StudyStore(mp,store.splits_path,store.cache)


def test_each_subject_once_per_epoch():
    order=epoch_order(174,42,1)
    assert sorted(order)==list(range(174))
    assert order==epoch_order(174,42,1)
    assert order!=epoch_order(174,42,2)
