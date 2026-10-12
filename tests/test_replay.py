import torch
from neurofusion.replay import state_equal


def test_nested_checkpoint_state_exactness():
    a={'state':{0:{'step':torch.tensor(3.),'moment':torch.tensor([1.,2.])}},'groups':[{'lr':.001}]}
    b={'state':{0:{'step':torch.tensor(3.),'moment':torch.tensor([1.,2.])}},'groups':[{'lr':.001}]}
    assert state_equal(a,b)
    b['state'][0]['moment'][1]+=1e-6
    assert not state_equal(a,b)
    assert not state_equal(torch.tensor([1.]),torch.tensor([1.],dtype=torch.float64))
    assert not state_equal({'x':1},{'x':1,'y':2})
