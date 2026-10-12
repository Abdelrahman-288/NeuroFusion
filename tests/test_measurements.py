import copy,itertools
import nibabel as nib
import numpy as np
import pytest
from neurofusion.inference import prepare_dwi_input,Predictor
from neurofusion.preprocessing import restore_prediction
from neurofusion.measurements import measure_regions,bind_evidence,validate_evidence


AFFINES=[]
for perm in itertools.permutations(range(3)):
    for signs in itertools.product((-1,1),repeat=3):
        a=np.eye(4);a[:3,:3]=np.eye(3)[:,perm]@np.diag(np.asarray(signs)*[2,3,4]);a[:3,3]=[13,-9,25];AFFINES.append(a)
AFFINES.append(np.array([[2,.3,.1,13],[.2,3,.4,-9],[0,.1,4,25],[0,0,0,1.]]))


@pytest.mark.parametrize('affine',AFFINES)
def test_physical_geometry_roundtrip_and_preview_coordinates(tmp_path,affine):
    p=np.zeros((5,6,7),dtype=np.float32);p[1:3,2,3]=.9;p[4,5,6]=.8
    image=nib.Nifti1Image(p,affine);image.header.set_xyzt_units('mm');path=tmp_path/'source.nii.gz';nib.save(image,path)
    _,meta=prepare_dwi_input(path);canonical=nib.as_closest_canonical(nib.load(path)).get_fdata(dtype=np.float32)
    m=measure_regions(canonical,meta)
    expected=abs(np.linalg.det(nib.load(path).affine[:3,:3]))*3/1000
    assert m['total_volume_ml']==pytest.approx(expected)
    assert sum(f['count'] for f in m['findings'])==3 and len(m['findings'])==2
    for f in m['findings']:
        native=nib.affines.apply_affine(np.linalg.inv(meta['original_affine']),nib.affines.apply_affine(meta['canonical_affine'],f['anchor_index']))
        np.testing.assert_allclose(native,np.round(native),atol=1e-6)
        assert p[tuple(np.round(native).astype(int))]>=.5
        row,col=f['preview_pixel_rc'];assert np.rot90(canonical[:,:,f['slice_index']])[row,col]>=.5
        np.testing.assert_allclose(nib.affines.apply_affine(meta['original_affine'],f['centroid_original_index']),f['centroid_ras_mm'],atol=1e-6)
    restore_prediction(canonical,meta,tmp_path/'restored.nii.gz')
    assert np.array_equal(nib.load(tmp_path/'restored.nii.gz').get_fdata(),p)


def test_units_and_transforms_rejected(tmp_path):
    x=np.arange(120,dtype=np.float32).reshape(4,5,6);im=nib.Nifti1Image(x,np.eye(4));im.header.set_xyzt_units('mm');nib.save(im,tmp_path/'x.nii')
    _,meta=prepare_dwi_input(tmp_path/'x.nii');p=(x>50).astype(np.float32)
    for field,value in [('xyzt_units',['meter','unknown']),('canonical_affine',np.diag([2,2,2,1]).tolist()),('original_affine',np.zeros((4,4)).tolist()),('canonical_shape',[5,5,6])]:
        broken=copy.deepcopy(meta);broken[field]=value
        with pytest.raises(ValueError):measure_regions(p,broken)
    with pytest.raises(ValueError):measure_regions(p)


def test_pixel_evidence_links_and_tampering(tmp_path):
    p=np.zeros((32,40),dtype=np.float32);p[5:8,10:12]=.8
    np.savez_compressed(tmp_path/'probability.npz',probability=p)
    result=dict(task='tumor-image',input_sha256='a'*64,models={'test':'b'*64},probability_file='probability.npz',views=[])
    Predictor.view(tmp_path,np.zeros((32,40,3),dtype=np.uint8),p>=.5,0,result)
    result['measurements']=bind_evidence(measure_regions(p),result,tmp_path)
    m=result['measurements'];assert m['total_volume_ml'] is None and m['count']==6
    assert validate_evidence(result,tmp_path)['findings']==1
    for field,value in [('preview_pixel_rc',[0,0]),('count',100)]:
        bad=copy.deepcopy(result);bad['measurements']['findings'][0][field]=value
        with pytest.raises(ValueError):validate_evidence(bad,tmp_path)
    bad=copy.deepcopy(result);bad['measurements']['findings'][0]['evidence']['image']['file']='../private.png'
    with pytest.raises(ValueError):validate_evidence(bad,tmp_path)
    (tmp_path/'image-000.png').write_bytes(b'altered')
    with pytest.raises(ValueError):validate_evidence(result,tmp_path)


def test_empty_prediction_and_threshold():
    assert measure_regions(np.zeros((3,4)))['findings']==[]
    assert measure_regions(np.array([[.5,.499]]))['count']==1
    with pytest.raises(ValueError):measure_regions(np.array([[np.nan]]))
