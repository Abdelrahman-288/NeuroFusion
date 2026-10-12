from types import SimpleNamespace
import numpy as np
import pytest
import torch
from neurofusion.ucsf_sampling import foreground_weights,compare_runs


def test_balancing_group_mass_and_repeatability():
    y=np.zeros((10,1,2,2),dtype=np.uint8);y[:2]=1
    d=SimpleNamespace(arrays=[(None,y)],index=[(0,z,'train') for z in range(10)])
    weights,flags=foreground_weights(d)
    assert weights[flags].sum().item()==pytest.approx(.5)
    assert weights[~flags].sum().item()==pytest.approx(.5)
    def draw():return list(torch.utils.data.WeightedRandomSampler(weights,1000,generator=torch.Generator().manual_seed(42)))
    assert draw()==draw()
    assert .44<flags[draw()].mean()<.56
    y[:]=0
    with pytest.raises(ValueError):foreground_weights(d)


def run(dices,fps):
    return {'final_epoch':{'cases':[{'patient_id':str(i),'metrics':{'dice':d,'iou':d/(2-d),'fp':fp,'voxel_ml':.001}} for i,(d,fp) in enumerate(zip(dices,fps))]}}


def test_guardrails_reject_mean_gain_with_patient_harm_or_extra_fp():
    b=run([.5,.5],[10,10])
    assert compare_runs(b,run([.6,.6],[9,10]))['all_passed']
    assert not compare_runs(b,run([.8,.44],[9,10]))['all_passed']
    assert not compare_runs(b,run([.6,.6],[11,10]))['all_passed']
    assert not compare_runs(b,b)['all_passed']
    with pytest.raises(ValueError):compare_runs(b,run([.6],[10]))
