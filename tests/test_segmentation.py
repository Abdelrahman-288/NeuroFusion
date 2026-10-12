import numpy as np
import torch
from neurofusion.segmentation import CompactUNet, metrics, predict_volume, sample_patch, segmentation_loss


def test_model_odd_shape_gradients():
    torch.set_num_threads(2)
    model=CompactUNet()
    x=torch.randn(1,1,9,11,13)
    target=torch.zeros_like(x)
    out=model(x)
    assert out.shape==x.shape
    loss=segmentation_loss(out,target)
    loss.backward()
    assert torch.isfinite(loss)
    assert all(torch.isfinite(p.grad).all() for p in model.parameters())


def test_sliding_window_covers_edges_and_padding():
    class Identity(torch.nn.Module):
        def forward(self,x): return x
    for shape in [(5,6,7),(13,17,19)]:
        x=np.random.default_rng(1).normal(size=shape).astype(np.float32)
        actual=predict_volume(Identity(),x,'cpu',patch=8)
        np.testing.assert_allclose(actual,1/(1+np.exp(-x)),atol=1e-6)


def test_empty_and_missed_lesion_metrics():
    zero=np.zeros((2,2,2))
    assert metrics(zero,zero)['dice']==1
    assert metrics(zero,np.ones_like(zero))['dice']==0
    assert metrics(np.ones_like(zero),zero)['false_positive_voxels']==8


def test_patch_padding_and_repeatability():
    x=np.ones((7,9,11),dtype=np.float32)
    a=sample_patch(x,x,np.random.default_rng(5),16)
    b=sample_patch(x,x,np.random.default_rng(5),16)
    assert a[0].shape==(16,16,16)
    np.testing.assert_array_equal(a[0],b[0])
