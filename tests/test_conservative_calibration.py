import numpy as np
import pytest
from neurofusion.conservative_calibration import select,transform


def test_identity_and_mixing_preserve_classes():
    p=np.asarray([[.8,.1,.1],[.2,.7,.1]])
    assert np.allclose(transform(p,1,0),p)
    q=transform(p,1.5,.1)
    assert np.allclose(q.sum(1),1)
    assert np.array_equal(q.argmax(1),p.argmax(1))
    with pytest.raises(ValueError):transform(p,1,1)


def test_selection_keeps_groups_together_and_is_deterministic():
    p=np.tile([.8,.2],(20,1));y=np.tile([0,0,0,1],5)
    groups=[str(i//2) for i in range(20)]
    a=select(p,y,groups);b=select(p,y,groups)
    assert a==b and a['selected']['eligible']
    for g in set(groups):assert len({f for f,k in zip(a['folds'],groups) if k==g})==1
    assert len(a['candidates'])==25


def test_identity_remains_available_for_perfect_probabilities():
    p=np.tile([1.,0.],(10,1));y=np.zeros(10,dtype=int)
    result=select(p,y,[str(i) for i in range(10)])
    assert result['identity_selected']
    with pytest.raises(ValueError):select(p,y,['one']*10)
