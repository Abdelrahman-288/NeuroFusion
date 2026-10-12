import pytest
import torch
from neurofusion.federated import aggregate

def update(client,value,count=1):return {'client':client,'samples':count,'state':{'weight':torch.tensor([value],dtype=torch.float32)}}

def test_weighted_updates_and_no_input_mutation():
    a=update('a',2.,1);b=update('b',6.,3)
    assert aggregate([a,b],['a','b'])['weight'].item()==5.
    assert a['state']['weight'].item()==2.

@pytest.mark.parametrize('updates',[[update('a',1.)],[update('a',1.),update('a',2.)],[update('a',1.),update('b',float('nan'))],[update('a',1.),update('b',2.,0)]])
def test_invalid_round_rejected(updates):
    with pytest.raises(ValueError):aggregate(updates,['a','b'])

def test_incompatible_update_rejected():
    a=update('a',1.);b=update('b',1.);b['state']['weight']=torch.tensor([1.,2.])
    with pytest.raises(ValueError):aggregate([a,b],['a','b'])
