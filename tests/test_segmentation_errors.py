import numpy as np
import pytest
from neurofusion.segmentation_errors import component_errors


def test_components_partial_overlap_missed_and_extra():
    r=np.zeros((8,8,8),dtype=np.uint8);p=r.copy()
    r[1:3,1,1]=1;r[6,6,6]=1
    p[1,1,1]=1;p[4,4,4]=1
    m=component_errors(p,r)
    assert m['reference_components_without_overlap']==1
    assert m['prediction_components_without_overlap']==1
    assert m['reference_components'][0]['overlap_fraction']==.5
    assert m['false_negative_voxels']==2 and m['false_positive_voxels']==1
    assert m['false_positive_voxels_on_reference_empty_slices']==1


def test_diagonal_connectivity_empty_and_rejection():
    r=np.zeros((3,3,3),dtype=np.uint8);p=r.copy()
    assert component_errors(p,r)['reference_components']==[]
    r[0,0,0]=1;r[1,1,1]=1
    assert len(component_errors(p,r)['reference_components'])==1
    with pytest.raises(ValueError):component_errors(p,r[:2])
    with pytest.raises(ValueError):component_errors(p,r*2)
