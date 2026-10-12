import nibabel as nib
import numpy as np
import pytest
from neurofusion.native_metrics import native_binary_metrics


def volume(values, affine=None):
    n=nib.Nifti1Image(np.asarray(values,dtype=np.float32),np.diag([2.,3.,4.,1.]) if affine is None else affine)
    n.header.set_xyzt_units('mm')
    return n


def test_hand_calculated_overlap_and_physical_volume():
    p=np.array([1,1,0,0]).reshape(2,2,1)
    t=np.array([1,0,1,0]).reshape(2,2,1)
    m=native_binary_metrics(volume(p),volume(t))
    assert (m['tp'],m['fp'],m['fn'],m['tn'])==(1,1,1,1)
    assert m['dice']==.5 and m['iou']==pytest.approx(1/3)
    assert m['reference_ml']==pytest.approx(.048)
    assert m['signed_volume_error_ml']==0


@pytest.mark.parametrize('pred,truth,state,dice,recall,precision',[
    (0,0,'both_empty',None,None,None),(1,0,'reference_empty',0,None,0),
    (0,1,'prediction_empty',0,0,None),(1,1,'both_nonempty',1,1,1)])
def test_empty_policies(pred,truth,state,dice,recall,precision):
    m=native_binary_metrics(volume(np.full((2,2,2),pred)),volume(np.full((2,2,2),truth)))
    assert (m['empty_state'],m['dice'],m['voxel_recall'],m['voxel_precision'])==(state,dice,recall,precision)


@pytest.mark.parametrize('value',[.5,2,np.nan])
def test_no_implicit_threshold_or_multiclass_conversion(value):
    with pytest.raises(ValueError): native_binary_metrics(volume(np.full((2,2,2),value)),volume(np.zeros((2,2,2))))


def test_translated_grid_rejected():
    a=np.diag([2.,3.,4.,1.]);a[0,3]=2
    with pytest.raises(ValueError,match='grids differ'):
        native_binary_metrics(volume(np.zeros((2,2,2)),a),volume(np.zeros((2,2,2))))


def test_conflicting_headers_and_unknown_units_rejected():
    p=volume(np.zeros((2,2,2)));p.set_qform(np.eye(4),code=1)
    with pytest.raises(ValueError,match='Conflicting'):native_binary_metrics(p,volume(np.zeros((2,2,2))))
    p=volume(np.zeros((2,2,2)));p.header.set_xyzt_units('unknown')
    with pytest.raises(ValueError,match='units'):native_binary_metrics(p,volume(np.zeros((2,2,2))))
