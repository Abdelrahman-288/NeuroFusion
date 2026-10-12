import numpy as np
import pytest
from neurofusion.augmentation import augment
from neurofusion.augmentation import augment_contrast


def test_augmentation_reproducible_bounded_and_nonmutating():
    x=np.linspace(0,1,4*128*128,dtype=np.float32).reshape(4,1,128,128); original=x.copy()
    a=augment(x,np.random.default_rng(1042));b=augment(x,np.random.default_rng(1042))
    assert np.array_equal(a,b) and np.array_equal(x,original)
    assert a.shape==x.shape and a.dtype==np.float32 and a.min()>=0 and a.max()<=1
    assert not np.array_equal(a,x)


def test_augmentation_state_restores_sequence_and_does_not_change_shuffle_rng():
    x=np.full((2,1,8,8),.5,dtype=np.float32);rng=np.random.default_rng(1042)
    state=rng.bit_generator.state
    a=augment(x,rng); rng.bit_generator.state=state
    assert np.array_equal(a,augment(x,rng))
    assert not np.array_equal(a,augment(x,rng))


def test_augmentation_rejects_invalid_values():
    with pytest.raises(ValueError): augment(np.ones((1,1,8,8))*2,np.random.default_rng(1))


def test_contrast_policy_preserves_center_and_changes_only_selected_images():
    center=np.full((100,1,8,8),.5,dtype=np.float32)
    assert np.array_equal(augment_contrast(center,np.random.default_rng(1042)),center)
    x=np.broadcast_to(np.linspace(0,1,64,dtype=np.float32).reshape(1,1,8,8),(100,1,8,8)).copy()
    a=augment_contrast(x,np.random.default_rng(1042));b=augment_contrast(x,np.random.default_rng(1042))
    assert np.array_equal(a,b) and a.min()>=0 and a.max()<=1
    changed=np.any(a!=x,axis=(1,2,3))
    assert 0<changed.sum()<len(x)
    assert np.all(np.abs(a-.5)<=np.abs(x-.5)+1e-7)
    with pytest.raises(ValueError):augment_contrast(x+2,np.random.default_rng(1))
