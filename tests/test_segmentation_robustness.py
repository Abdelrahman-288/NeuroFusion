import numpy as np
import pytest
from neurofusion.segmentation_robustness import perturb_dwi,paired_metrics,summarize_cases,DWI_CONDITIONS


def test_dwi_domain_and_determinism():
    x=np.linspace(-3,4,120,dtype=np.float32).reshape(4,5,6)
    assert np.array_equal(perturb_dwi(x,'clean',1),x)
    assert perturb_dwi(x,'scale_120',1).max()>1
    assert np.array_equal(perturb_dwi(x,'noise_010',1),perturb_dwi(x,'noise_010',1))
    assert not np.array_equal(perturb_dwi(x,'noise_010',1),perturb_dwi(x,'noise_010',2))
    for c in DWI_CONDITIONS:assert perturb_dwi(x,c,1).shape==x.shape
    with pytest.raises(ValueError):perturb_dwi(x,'unknown',1)
    with pytest.raises(ValueError):perturb_dwi(x[:,:,0],'clean',1)


def test_new_miss_and_physical_metrics():
    y=np.array([1,0,0]);clean=np.array([.9,.1,.1]);p=np.array([.1,.9,.9])
    r=paired_metrics(p,y,clean,.002)
    assert r['new_zero_overlap'] and r['dice_change']==-1
    assert r['false_positive']==.004 and r['volume_error']==.002
    assert r['mask_flip_fraction']==1
    summary=summarize_cases([dict(id='case',**r)])
    assert summary['new_zero_overlap']==['case']
    assert all(summary['development_flags'].values())
    assert paired_metrics(clean,y,p)['recovered_overlap']


def test_clean_identity_and_invalid_predictions():
    p=np.array([.5,.2]);y=np.array([1,0])
    r=paired_metrics(p,y,p)
    assert r['dice']==1 and r['dice_change']==0 and r['probability_mae']==0
    with pytest.raises(ValueError):paired_metrics(p,y[:1],p)
    with pytest.raises(ValueError):paired_metrics(np.array([np.nan,.2]),y,p)
    with pytest.raises(ValueError):paired_metrics(p,y,p,0)
