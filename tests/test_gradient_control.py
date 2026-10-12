import pytest
import torch
from neurofusion.gradient_control import clip_unscaled_gradients


def test_global_clipping_preserves_direction_and_small_gradients():
    a=torch.nn.Parameter(torch.zeros(1));b=torch.nn.Parameter(torch.zeros(1))
    a.grad=torch.tensor([3.]);b.grad=torch.tensor([4.])
    before,after=clip_unscaled_gradients([a,b])
    assert before==5 and after<=1.000001
    assert a.grad.item()==pytest.approx(.6,abs=1e-6)
    assert b.grad.item()==pytest.approx(.8,abs=1e-6)
    a.grad=torch.tensor([.1]);b.grad=torch.tensor([.2])
    clip_unscaled_gradients([a,b]);assert a.grad.item()==pytest.approx(.1)


def test_clipping_rejects_nonfinite_gradients_and_invalid_limit():
    p=torch.nn.Parameter(torch.zeros(1));p.grad=torch.tensor([float('inf')])
    with pytest.raises(RuntimeError):clip_unscaled_gradients([p])
    with pytest.raises(ValueError):clip_unscaled_gradients([p],0)
