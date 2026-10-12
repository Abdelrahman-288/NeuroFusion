import nibabel as nib
import numpy as np
from neurofusion.data import inspect_volume


def test_unknown_units_do_not_invent_milliliters(tmp_path):
    path=tmp_path/'mask.nii'
    image=nib.Nifti1Image(np.ones((3,3,3),dtype=np.uint8),np.eye(4))
    nib.save(image,path)
    assert inspect_volume(path,mask=True)['lesion_volume_ml'] is None
    image.header.set_xyzt_units('mm')
    nib.save(image,path)
    assert abs(inspect_volume(path,mask=True)['lesion_volume_ml']-.027)<1e-8
