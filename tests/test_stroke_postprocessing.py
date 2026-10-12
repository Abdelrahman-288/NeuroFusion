import numpy as np
import pytest
from neurofusion.stroke_postprocessing import threshold_components


def test_filter_uses_physical_volume_and_preserves_threshold():
    p=np.zeros((5,5,5));p[0,0,0]=.9;p[3:5,3:5,3:5]=.55
    m=threshold_components(p,.002)
    assert not m[0,0,0] and m.sum()==8
    assert threshold_components(p,.02).sum()==9


def test_diagonal_connectivity_and_empty_input():
    p=np.zeros((3,3,3));p[0,0,0]=p[1,1,1]=.7
    assert threshold_components(p,.005).sum()==2
    assert not threshold_components(p*0,.005).any()


def test_invalid_probabilities_and_scale():
    with pytest.raises(ValueError):threshold_components(np.ones((2,2)),.01)
    with pytest.raises(ValueError):threshold_components(np.ones((2,2,2)),0)
    with pytest.raises(ValueError):threshold_components(np.full((2,2,2),np.nan),.01)
