import torch
from neurofusion.ct_model import HemorrhageCNN

def test_six_outputs_learn_from_all_ct_windows():
    torch.set_num_threads(2);torch.manual_seed(42)
    model=HemorrhageCNN();x=torch.randn(2,3,32,32,requires_grad=True)
    logits=model(x);assert logits.shape==(2,6)
    torch.nn.functional.binary_cross_entropy_with_logits(logits,torch.ones_like(logits)).backward()
    assert all(x.grad[:,i].abs().sum()>0 for i in range(3))
