import numpy as np
import pytest
from neurofusion.ucsf_diagnostics import probability_diagnostics


def test_threshold_histograms_and_empty_slice_errors():
    p=np.array([[[.49,.5]],[[.9,.1]]],dtype=np.float32);y=np.array([[[1,0]],[[0,0]]])
    r=probability_diagnostics(p,y)
    assert r['foreground']['voxels_ge_05']==0
    assert r['background']['voxels_ge_05']==2
    assert sum(r['background']['histogram_20_bins'])==3
    assert r['slices']['fp_voxels_on_reference_empty_slices']==1
    assert r['predicted_fraction']==.5


def test_empty_groups_and_invalid_values():
    p=np.zeros((2,2,2),dtype=np.float32);y=np.zeros_like(p)
    assert probability_diagnostics(p,y)['foreground']['mean_probability'] is None
    for invalid in [p+np.nan,p+1.1]:
        with pytest.raises(ValueError):probability_diagnostics(invalid,y)
    with pytest.raises(ValueError):probability_diagnostics(p,y+2)
