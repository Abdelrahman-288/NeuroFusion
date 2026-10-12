import numpy as np
import pytest
from neurofusion.volume_similarity import fingerprint,similarity


def test_scaled_copy_is_flagged_but_unrelated_content_is_not():
    rng=np.random.default_rng(42)
    a=rng.uniform(1,100,(24,24,24)).astype(np.float32)
    assert similarity(fingerprint(a),fingerprint(a*3))>.995
    assert similarity(fingerprint(a),fingerprint(rng.uniform(1,100,a.shape)))<.995


@pytest.mark.parametrize('a',[np.zeros((5,5,5)),np.ones((5,5,5)),np.ones((5,5)),np.full((5,5,5),np.nan)])
def test_invalid_inputs_are_not_silently_cleared(a):
    with pytest.raises(ValueError):fingerprint(a)


def test_invalid_fingerprint_comparison_is_rejected():
    with pytest.raises(ValueError):similarity(np.zeros(3),np.zeros(3))
