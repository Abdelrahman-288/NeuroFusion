import numpy as np
import pytest
import torch
from neurofusion.tumor import TumorCNN,classification_metrics,load_partition


def test_four_class_metrics_and_confusion_direction():
    labels=np.array([0,0,1,2,3])
    probs=np.eye(4)[[0,1,1,2,3]]
    result=classification_metrics(labels,probs)
    assert result['accuracy']==.8
    assert result['confusion_matrix'][0]==[1,1,0,0]
    assert result['per_class'][0]['recall']==.5
    assert result['balanced_accuracy']==.875
    assert result['macro_f1']==pytest.approx((2/3+2/3+1+1)/4)
    with pytest.raises(ValueError): classification_metrics(labels,probs*2)


def test_model_output_and_development_partition_guard(tmp_path):
    model=TumorCNN()
    logits=model(torch.zeros(2,1,128,128))
    assert logits.shape==(2,4)
    logits.sum().backward()
    for partition in ['test','quarantine']:
        with pytest.raises(ValueError,match='refuses'):
            load_partition(tmp_path,tmp_path/'missing.json',partition)


@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA unavailable')
def test_deterministic_gpu_training_step(monkeypatch):
    monkeypatch.setenv('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    previous=torch.are_deterministic_algorithms_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        model=TumorCNN().cuda()
        loss=torch.nn.functional.cross_entropy(model(torch.zeros(2,1,128,128,device='cuda')),torch.tensor([0,1],device='cuda'))
        loss.backward()
        assert torch.isfinite(loss)
    finally:
        torch.use_deterministic_algorithms(previous)
