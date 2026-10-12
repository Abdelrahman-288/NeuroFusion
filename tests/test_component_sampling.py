import numpy as np
from neurofusion.segmentation import component_coordinates, sample_patch


def test_balances_unequal_components_and_preserves_background_branch():
    mask=np.zeros((30,30,30),dtype=np.uint8)
    mask[2,2,2]=1
    mask[15:25,15:25,15:25]=1
    image=np.zeros_like(mask,dtype=np.float32)
    image[2,2,2]=1
    image[15:25,15:25,15:25]=2
    groups=component_coordinates(mask)
    assert sorted(map(len,groups))==[1,1000]
    rng=np.random.default_rng(42)
    values=[int(sample_patch(image,mask,rng,size=1,components=groups)[0].item()) for _ in range(4000)]
    small,large=values.count(1),values.count(2)
    assert 800<small<1200
    assert 800<large<1300
    assert values.count(0)>1500
    baseline=np.random.default_rng(42)
    assert sum(sample_patch(image,mask,baseline,size=1)[0].item()==1 for _ in range(1000))<10


def test_empty_padding_and_deterministic_component_samples():
    mask=np.zeros((3,4,5),dtype=np.uint8)
    image=mask.astype(np.float32)
    groups=component_coordinates(mask)
    assert groups==[]
    x,y=sample_patch(image,mask,np.random.default_rng(1),size=8,components=groups)
    assert x.shape==y.shape==(8,8,8)
    assert not y.any()
    mask[0,0,0]=1
    mask[1,1,1]=1
    groups=component_coordinates(mask)
    assert len(groups)==1  # Diagonally touching voxels use 26-connectivity.
    a,b=np.random.default_rng(7),np.random.default_rng(7)
    for _ in range(20):
        xa,ya=sample_patch(image,mask,a,size=2,components=groups)
        xb,yb=sample_patch(image,mask,b,size=2,components=groups)
        assert np.array_equal(xa,xb) and np.array_equal(ya,yb)
