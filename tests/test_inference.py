import numpy as np
import nibabel as nib
import pytest
from neurofusion.inference import prepare_dwi_input,Predictor
from neurofusion.preprocessing import prepare_dwi


def test_label_free_dwi_preprocessing_matches_training(tmp_path):
    values=np.arange(4*5*6,dtype=np.float32).reshape(4,5,6)
    affine=np.diag([-2,2,2,1]); image=nib.Nifti1Image(values,affine)
    image.header.set_xyzt_units('mm'); path=tmp_path/'dwi.nii.gz'; nib.save(image,path)
    mask=nib.Nifti1Image((values>50).astype(np.uint8),affine); mask.header.set_xyzt_units('mm')
    mp=tmp_path/'mask.nii.gz'; nib.save(mask,mp)
    x,meta=prepare_dwi_input(path)
    old=prepare_dwi(path,mp,tmp_path/'prepared')
    expected=nib.load(tmp_path/'prepared/dwi.nii.gz').get_fdata(dtype=np.float32)
    assert np.array_equal(x,expected)
    for key in ['original_shape','original_affine','canonical_shape','canonical_affine','inverse_orientation']:
        assert meta[key]==old[key]


def test_invalid_dwi_and_task_rejected(tmp_path):
    image=nib.Nifti1Image(np.zeros((4,4,4),dtype=np.float32),np.eye(4))
    path=tmp_path/'dwi.nii'; nib.save(image,path)
    with pytest.raises(ValueError,match='millimeter'): prepare_dwi_input(path)
    image.header.set_xyzt_units('mm'); nib.save(image,path)
    with pytest.raises(ValueError,match='variation'): prepare_dwi_input(path)
    with pytest.raises(ValueError,match='Unsupported task'):
        Predictor(tmp_path,'cpu').analyze(path,'ct',tmp_path/'out')
