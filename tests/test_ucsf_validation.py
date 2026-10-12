import nibabel as nib
import numpy as np
import pytest
from neurofusion.external_adapter import prepare_pair
from neurofusion.ucsf_validation import score_native, aggregate_cases


def test_native_union_reconstruction_with_flipped_axes(tmp_path):
    shape=(16,16,8); affine=np.diag([-1.,1.,-1.,1.])
    labels=np.zeros(shape,dtype=np.uint8)
    labels[2:7,3:10,1:4]=1;labels[8:12,9:14,4:6]=4
    paths=[]
    for name,data in [('image',np.arange(np.prod(shape),dtype=np.float32).reshape(shape)),('mask',labels)]:
        im=nib.Nifti1Image(data,affine);im.header.set_xyzt_units('mm')
        path=tmp_path/(name+'.nii.gz');nib.save(im,path);paths.append(path)
    _,masks,geometry=prepare_pair(*paths,allowed_labels=[0,1,2,4],size=16)
    metrics,prediction=score_native((masks>0).astype(np.float32),geometry,nib.load(paths[1]))
    assert metrics['dice']==1 and metrics['absolute_volume_error_ml']==0
    assert np.array_equal(prediction.get_fdata(),labels>0)
    wrong=nib.Nifti1Image(labels,np.eye(4));wrong.header.set_xyzt_units('mm')
    with pytest.raises(ValueError,match='Native grids differ'):score_native((masks>0).astype(np.float32),geometry,wrong)


def test_aggregation_preserves_undefined_and_patient_weighting():
    def case(patient,dice,state):
        return {'patient_id':patient,'metrics':dict(empty_state=state,dice=dice,iou=dice,voxel_recall=dice,voxel_precision=dice,absolute_volume_error_ml=0)}
    cases=[case('a',None,'both_empty'),case('b',0,'prediction_empty'),case('c',1,'both_nonempty')]
    result=aggregate_cases(cases)
    assert result['dice']=={'mean':.5,'defined':2,'undefined':1}
    assert result['empty_states']['both_empty']==1
    with pytest.raises(ValueError):aggregate_cases(cases+[cases[0]])
