import numpy as np
import pytest
from neurofusion.robustness import perturb,summarize,CONDITIONS


def test_deterministic_noise_and_clean_identity():
    values=np.linspace(0,1,128*128,dtype=np.float32).reshape(1,1,128,128)
    assert np.array_equal(values,perturb(values,'clean'))
    assert np.array_equal(perturb(values,'noise_003',42),perturb(values,'noise_003',42))
    assert not np.array_equal(perturb(values,'noise_003',42),perturb(values,'noise_003',43))
    for name in CONDITIONS:
        actual=perturb(values,name)
        assert actual.shape==values.shape and 0<=actual.min()<=actual.max()<=1


def test_blur_does_not_mix_images():
    images=np.stack([np.zeros((1,8,8)),np.ones((1,8,8))]).astype(np.float32)
    assert np.array_equal(perturb(images,'blur_100'),images)


def test_paired_errors_and_group_weights():
    clean=np.eye(4)[[0,1,0]];changed=np.eye(4)[[1,1,2]]
    metrics=summarize([0,1,2],changed,clean,['a','a','b'])
    assert metrics['correct_to_wrong']==1 and metrics['wrong_to_correct']==1
    assert metrics['flip_rate']==2/3 and metrics['equal_group_accuracy']==.75


def test_invalid_protocol_inputs():
    with pytest.raises(ValueError): perturb(np.ones((1,1,4,4))*2,'clean')
    with pytest.raises(ValueError): perturb(np.ones((1,1,4,4)),'unknown')
