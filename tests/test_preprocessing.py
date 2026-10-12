import nibabel as nib
import numpy as np
import pytest
from neurofusion.preprocessing import prepare_dwi, restore_prediction


@pytest.mark.parametrize('affine', [np.diag([-2., 3., -4., 1.]),
    np.array([[0,0,-4,10],[2,0,0,20],[0,-3,0,30],[0,0,0,1.]])])
def test_native_grid_roundtrip(tmp_path, affine):
    image = np.arange(5*6*7, dtype=np.float32).reshape(5,6,7)
    mask = (image > 120).astype(np.uint8)
    source = nib.Nifti1Image(image, affine)
    source.header.set_xyzt_units('mm')
    nib.save(source, tmp_path/'image.nii.gz')
    label = nib.Nifti1Image(mask, affine)
    label.header.set_xyzt_units('mm')
    nib.save(label, tmp_path/'mask.nii.gz')
    meta = prepare_dwi(tmp_path/'image.nii.gz', tmp_path/'mask.nii.gz', tmp_path/'processed')
    canonical = nib.load(tmp_path/'processed/mask.nii.gz')
    assert nib.aff2axcodes(canonical.affine) == ('R','A','S')
    restore_prediction(canonical.get_fdata(), meta, tmp_path/'restored.nii.gz')
    restored = nib.load(tmp_path/'restored.nii.gz')
    np.testing.assert_array_equal(restored.get_fdata(), mask)
    np.testing.assert_allclose(restored.affine, affine)
    assert restored.header.get_xyzt_units()[0] == 'mm'
    normalized = nib.load(tmp_path/'processed/dwi.nii.gz').get_fdata()
    foreground = normalized[normalized != 0]
    assert abs(foreground.mean()) < 1e-5


def test_misaligned_pair_rejected(tmp_path):
    image = np.arange(64,dtype=np.float32).reshape(4,4,4)
    nib.save(nib.Nifti1Image(image,np.eye(4)),tmp_path/'dwi.nii')
    nib.save(nib.Nifti1Image((image>30).astype(np.uint8),np.diag([2,2,2,1.])),tmp_path/'mask.nii')
    with pytest.raises(ValueError, match='physical grid'):
        prepare_dwi(tmp_path/'dwi.nii',tmp_path/'mask.nii',tmp_path/'out')
