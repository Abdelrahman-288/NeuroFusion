import numpy as np
import pytest
from neurofusion.calibration import group_partition,scale,fit_temperature,metrics


def test_group_roles_do_not_depend_on_row_order_or_split_duplicates():
    groups=['a','b','a','c','d'];roles=group_partition(groups)
    assert roles[0]==roles[2]
    assert np.array_equal(group_partition(list(reversed(groups))),roles[::-1])
    assert roles.any() and (~roles).any()


def test_scaling_preserves_classes_and_normalization():
    p=np.array([[.9,.1],[.2,.8]])
    assert np.allclose(scale(p,1),p)
    scaled=scale(p,2)
    assert np.array_equal(scaled.argmax(1),p.argmax(1))
    assert np.allclose(scaled.sum(1),1)
    assert np.all(scaled.max(1)<p.max(1))


def test_fit_reduces_overconfidence_nll():
    p=np.tile([.99,.01],(10,1));y=np.array([0]*6+[1]*4)
    t=fit_temperature(p,y)
    assert t>1
    assert metrics(scale(p,t),y)['nll']<metrics(p,y)['nll']


def test_perfect_probabilities_and_empty_bins():
    result=metrics(np.eye(2),np.array([0,1]))
    assert result['nll']==0 and result['brier_multiclass_sum']==0
    assert result['ece_10_equal_width']==0
    assert result['reliability_bins'][-1]['count']==2
    assert result['reliability_bins'][0]['accuracy'] is None


@pytest.mark.parametrize('p',[[[.5,.7]],[[np.nan,0]],[[1.1,-.1]],[]])
def test_invalid_probabilities_rejected(p):
    with pytest.raises(ValueError):scale(p,1)
