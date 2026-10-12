import nibabel as nib
import numpy as np
import pytest
import torch
from neurofusion.fusion import load_aligned_adc
from neurofusion.segmentation import CompactUNet,sample_patch,predict_volume


def test_adc_geometry_and_intensity(tmp_path):
    values=np.arange(64,dtype=np.float32).reshape(4,4,4)
    path=tmp_path/'adc.nii.gz'
    image=nib.Nifti1Image(values,np.eye(4))
    image.header.set_xyzt_units('mm')
    nib.save(image,path)
    meta={'canonical_shape':[4,4,4],'canonical_affine':np.eye(4).tolist(),'xyzt_units':['mm','unknown']}
    result,stats=load_aligned_adc(path,meta)
    assert abs(result[values!=0].mean())<1e-6
    assert abs(result[values!=0].std()-1)<1e-6
    assert result[0,0,0]==0
    meta['canonical_affine'][0][3]=1
    with pytest.raises(ValueError,match='physical grid'):
        load_aligned_adc(path,meta)
    meta['canonical_affine']=np.eye(4).tolist()
    meta['xyzt_units'][0]='meter'
    with pytest.raises(ValueError,match='units'):
        load_aligned_adc(path,meta)


def test_joint_channel_crop_and_multichannel_inference():
    x=np.arange(12**3,dtype=np.float32).reshape(12,12,12)
    image=np.stack([x,x+100])
    mask=np.zeros_like(x,dtype=np.uint8)
    mask[4,4,4]=1
    patch,label=sample_patch(image,mask,np.random.default_rng(42),size=8)
    assert patch.shape==(2,8,8,8) and label.shape==(8,8,8)
    assert np.all(patch[1]-patch[0]==100)
    class ChannelDifference(torch.nn.Module):
        def forward(self,tensor):
            return tensor[:,1:2]-tensor[:,:1]-100
    result=predict_volume(ChannelDifference(),image,'cpu',patch=8)
    assert result.shape==mask.shape
    assert np.allclose(result,.5)
    model=CompactUNet(in_channels=2)
    output=model(torch.zeros(1,2,8,8,8))
    output.mean().backward()
    assert output.shape==(1,1,8,8,8)
