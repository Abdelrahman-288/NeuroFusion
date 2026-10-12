import numpy as np
import pytest
import torch
from neurofusion.tumor_segmentation import binary_mask,native_probability,mask_metrics,TumorUNet,segmentation_loss


def test_near_binary_policy_rejects_unexpected_mask_values():
    a=np.array([[0,10,246,255]],dtype=np.uint8)
    assert binary_mask(a).tolist()==[[0,0,1,1]]
    with pytest.raises(ValueError): binary_mask(np.array([[127]],dtype=np.uint8))
    with pytest.raises(ValueError): binary_mask(np.array([[1.]],dtype=np.float32))


def test_native_resize_and_overlap_metrics():
    p=native_probability(np.ones((8,8),dtype=np.float32),(24,32))
    assert p.shape==(24,32) and np.all(p==1)
    assert mask_metrics(p,np.ones_like(p))['dice']==1
    assert mask_metrics(np.zeros_like(p),np.ones_like(p))['dice']==0
    with pytest.raises(ValueError): mask_metrics(p,np.ones((3,3)))


@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA unavailable')
def test_deterministic_segmentation_backward(monkeypatch):
    monkeypatch.setenv('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    previous=torch.are_deterministic_algorithms_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        model=TumorUNet().cuda()
        logits=model(torch.zeros(2,1,32,32,device='cuda'))
        loss=segmentation_loss(logits,torch.zeros_like(logits))
        loss.backward()
        assert torch.isfinite(loss) and logits.shape==(2,1,32,32)
    finally: torch.use_deterministic_algorithms(previous)
