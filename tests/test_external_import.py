import hashlib
import nibabel as nib
import numpy as np
import pytest
from neurofusion.external_import import import_pilot


def fixture(tmp_path):
    pilot={'records':[{'exam_id':'case-1','patient_id':'p1'},{'exam_id':'case-2','patient_id':'p2'}]}
    row={'exam_id':'case-1','patient_id':'p1','allowed_labels':[0,2],'label_source':'Synthetic control label 2; not UCSF semantics'}
    for key in ('image','mask'):
        array=np.arange(512,dtype=np.float32).reshape(8,8,8) if key=='image' else np.zeros((8,8,8),dtype=np.float32)
        volume=nib.Nifti1Image(array,np.eye(4));volume.header.set_xyzt_units('mm')
        path=tmp_path/f'{key}.nii.gz';nib.save(volume,path)
        row[key]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return pilot,{'records':[row]}


def test_prepared_and_missing_are_distinct(tmp_path):
    pilot,manifest=fixture(tmp_path)
    summary=import_pilot(tmp_path,pilot,manifest,tmp_path/'out')
    assert summary['prepared']==1 and summary['awaiting_files']==1 and summary['failed']==0
    assert not summary['evaluation_ready'] and not summary['model_inference_performed']
    assert (tmp_path/'out/case-1/geometry.json').exists()


@pytest.mark.parametrize('change',['identity','escape','checksum','duplicate','reuse'])
def test_bad_declarations(tmp_path,change):
    pilot,manifest=fixture(tmp_path);row=manifest['records'][0]
    if change=='identity':row['patient_id']='wrong'
    if change=='escape':row['image']['path']='../outside.nii.gz'
    if change=='checksum':row['image']['sha256']='bad'
    if change=='duplicate':manifest['records'].append(row.copy())
    if change=='reuse':row['mask']=row['image'].copy()
    with pytest.raises(ValueError):import_pilot(tmp_path,pilot,manifest,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_changed_file_fails_without_prepared_arrays(tmp_path):
    pilot,manifest=fixture(tmp_path)
    (tmp_path/'image.nii.gz').write_bytes(b'changed')
    result=import_pilot(tmp_path,pilot,manifest,tmp_path/'out')
    assert result['failed']==1 and result['prepared']==0
    assert not (tmp_path/'out/case-1').exists()


def test_empty_manifest_reports_all_missing(tmp_path):
    pilot,_=fixture(tmp_path)
    result=import_pilot(tmp_path,pilot,{'records':[]},tmp_path/'out')
    assert result['awaiting_files']==2 and result['prepared']==0
