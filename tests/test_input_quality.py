import json
import nibabel as nib
import numpy as np
from PIL import Image
import pytest
from neurofusion.input_quality import inspect_input, InputQualityError
from neurofusion.inference import Predictor
from neurofusion.jobs import JobStore


def test_constant_image_rejected_before_model_loading(tmp_path, monkeypatch):
    path=tmp_path/'blank.png'; Image.new('L',(128,128),100).save(path)
    predictor=Predictor(tmp_path,'cpu')
    monkeypatch.setattr(predictor,'model',lambda key: pytest.fail('Model should not be loaded'))
    with pytest.raises(InputQualityError,match='no grayscale intensity variation'):
        predictor.analyze(path,'tumor-image',tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_low_contrast_is_warning_not_rejection(tmp_path):
    path=tmp_path/'low.png'; pixels=np.full((128,128),100,dtype=np.uint8); pixels[::2]=101
    Image.fromarray(pixels).save(path)
    report=inspect_input(path,'tumor-image')
    assert not report['errors'] and not report['modality_verified']
    assert any('Low grayscale contrast' in x for x in report['warnings'])


def test_color_small_and_aspect_warnings(tmp_path):
    path=tmp_path/'color.png'; values=np.zeros((32,128,3),dtype=np.uint8); values[:,:,0]=np.arange(128)
    Image.fromarray(values).save(path)
    report=inspect_input(path,'tumor-image')
    assert not report['errors']
    assert len(report['warnings'])==4


def test_transparency_rejected(tmp_path):
    path=tmp_path/'alpha.png'; Image.new('RGBA',(128,128),(100,100,100,0)).save(path)
    assert 'Transparent' in inspect_input(path,'tumor-image')['errors'][0]


@pytest.mark.parametrize('case',['4d','nonfinite','units','constant','corrupt'])
def test_bad_dwi_rejected(tmp_path,case):
    path=tmp_path/'scan.nii'
    if case=='corrupt': path.write_bytes(b'not nifti')
    else:
        shape=(16,16,16,2) if case=='4d' else (16,16,16)
        values=np.arange(np.prod(shape),dtype=np.float32).reshape(shape)
        if case=='nonfinite': values[0,0,0]=np.nan
        if case=='constant': values[:]=1
        image=nib.Nifti1Image(values,np.eye(4))
        if case!='units': image.header.set_xyzt_units('mm')
        nib.save(image,path)
    assert inspect_input(path,'stroke-dwi')['status']=='rejected'


def test_anisotropy_warning_and_metrics(tmp_path):
    path=tmp_path/'dwi.nii'; image=nib.Nifti1Image(np.arange(4096,dtype=np.float32).reshape(16,16,16),np.diag([1,1,6,1]))
    image.header.set_xyzt_units('mm'); nib.save(image,path)
    report=inspect_input(path,'stroke-dwi')
    assert not report['errors']
    assert report['metrics']['voxel_spacing_mm']==[1,1,6]
    assert any('anisotropic' in x for x in report['warnings'])


def test_rejection_reason_persists_in_job_history(tmp_path):
    store=JobStore(tmp_path/'jobs',Predictor(tmp_path,'cpu'))
    source=tmp_path/'blank.png'; Image.new('L',(128,128),0).save(source)
    job=store.submit(source.read_bytes(),'tumor-image','blank.png','.png')['id']
    store.run_one()
    assert store.get(job)['status']=='failed'
    assert 'Input rejected:' in store.get(job)['error']
    saved=json.loads((store.root/'quality'/(job+'.json')).read_text())
    assert saved['status']=='rejected'
