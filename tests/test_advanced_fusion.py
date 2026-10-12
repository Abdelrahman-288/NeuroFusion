import numpy as np
import pytest
import torch
from neurofusion.advanced_fusion import *


def test_separate_encoders_have_gradients_and_missing_branch_cannot_leak():
    torch.set_num_threads(2);torch.manual_seed(42)
    model=SeparateEncoderUNet();x=torch.randn(1,4,8,8,8);x[:,2:]=1
    model(x).mean().backward()
    assert model.dwi.a[0].weight.grad.abs().sum()>0
    assert model.adc.a[0].weight.grad.abs().sum()>0
    x[:,3]=0
    with torch.no_grad():
        first=model(x);x[:,1]=10000;second=model(x)
    assert torch.equal(first,second)
    x[:,2]=0
    with pytest.raises(ValueError):model(x)


def test_modality_input_rejects_absence_bad_grid_and_nan():
    x=np.ones((8,8,8),dtype=np.float32)
    assert modality_input(x,None).shape==(4,8,8,8)
    assert not modality_input(None,x)[2].any()
    with pytest.raises(ValueError):modality_input()
    with pytest.raises(ValueError):modality_input(x,np.zeros((2,2,2)))
    with pytest.raises(ValueError):modality_input(x*np.nan)


def test_ensemble_and_uncertainty_do_not_masquerade_as_confidence():
    p,v=ensemble_probabilities([[.1,.9],[.9,.1]])
    assert np.allclose(p,.5) and np.all(v>0)
    assert entropy([.5])[0]>entropy([.01])[0]
    with pytest.raises(ValueError):ensemble_probabilities([[np.nan]])


def test_calibration_metrics_and_temperature():
    p=np.array([.1,.9]);y=np.array([0,1])
    assert np.allclose(temperature_scale(p,1),p)
    assert np.array_equal(temperature_scale(p,2)>=.5,p>=.5)
    assert reliability(p,y)['brier']<reliability(1-p,y)['brier']
    with pytest.raises(ValueError):temperature_scale(p,0)
    with pytest.raises(ValueError):reliability(p,[0,2])
def test_default_inference_never_adds_underperforming_members():
    from neurofusion.advanced_fusion import inference_members
    assert inference_members(has_dwi=True,has_adc=True)==['dwi-component-001']
    assert inference_members(has_dwi=True,has_adc=False)==['dwi-component-001']
    assert len(inference_members(has_dwi=True,has_adc=True,experimental=True))==3
    assert len(inference_members(has_dwi=True,has_adc=False,experimental=True))==2
    for adc in (True,False):
        with pytest.raises(ValueError,match='DWI required'):
            inference_members(has_dwi=False,has_adc=adc,experimental=True)

