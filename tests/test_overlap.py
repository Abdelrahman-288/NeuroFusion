import numpy as np
import pytest
from PIL import Image

from neurofusion.overlap import fingerprint, index_images, screen_overlap


def test_reencoded_pixels_and_patient_propagation(tmp_path):
    pixels = np.random.default_rng(12).integers(0, 256, (64, 64), dtype=np.uint8)
    Image.fromarray(pixels).save(tmp_path/'a.png', compress_level=0)
    Image.fromarray(pixels).save(tmp_path/'b.png', compress_level=9)
    a, b = fingerprint(tmp_path/'a.png'), fingerprint(tmp_path/'b.png')
    assert a['sha256'] != b['sha256']
    assert a['pixel_sha256'] == b['pixel_sha256']
    ref = [{'path': 'ref', 'patient_id': None, **a}]
    candidates = [{'path': 'copy', 'patient_id': 'p1', **b},
                  {'path': 'other-slice', 'patient_id': 'p1', **b,
                   'sha256': 'other', 'pixel_sha256': 'other', 'phash': a['phash'] ^ ((1 << 63)-1)}]
    result = screen_overlap(ref, candidates)
    assert result['matches'][0]['kind'] == 'exact_pixels'
    assert result['patient_propagated_images'] == 1
    assert not result['evaluation_ready']


def test_similarity_threshold_and_zero_match_not_certification():
    ref = [{'path': 'r', 'sha256': 'a', 'pixel_sha256': 'a', 'phash': 0}]
    def candidate(code):
        return {'path': 'c', 'sha256': 'b', 'pixel_sha256': 'b', 'phash': code,
                'patient_id': None, 'constant': False}
    assert screen_overlap(ref, [candidate(15)])['similarity_only_images'] == 1
    result = screen_overlap(ref, [candidate(31)])
    assert not result['matches'] and not result['evaluation_ready']
    assert result['missing_candidate_patient_ids'] == 1
    with pytest.raises(ValueError):
        screen_overlap([], [candidate(31)])


def test_manifest_rejects_escape_duplicate_and_changed_file(tmp_path):
    Image.fromarray(np.zeros((8, 8), dtype=np.uint8)).save(tmp_path/'a.png')
    for rows in ([{'path': '../outside.png'}], [{'path': 'a.png'}]*2,
                 [{'path': 'a.png', 'sha256': 'wrong'}], []):
        with pytest.raises(ValueError):
            index_images(tmp_path, rows)
    assert index_images(tmp_path, [{'path': 'a.png'}])[0]['constant']
