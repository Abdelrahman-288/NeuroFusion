import nibabel as nib
import numpy as np
import pytest
from neurofusion.fusion_inputs import prepare_inputs


def write(path,shift=0):
    affine=np.eye(4);affine[0,3]=shift
    image=nib.Nifti1Image(np.arange(512,dtype=np.float32).reshape(8,8,8),affine)
    image.header.set_xyzt_units('mm');nib.save(image,path)


def test_missing_input_and_physical_alignment(tmp_path):
    a=tmp_path/'a.nii.gz';b=tmp_path/'b.nii.gz';write(a);write(b,1)
    arrays,meta=prepare_inputs(None,a)
    assert list(arrays)==['adc'] and meta['reference_modality']=='adc'
    with pytest.raises(ValueError,match='physical grid'):prepare_inputs(a,b)
    with pytest.raises(ValueError):prepare_inputs()
    write(b);arrays,_=prepare_inputs(a,b)
    assert np.array_equal(arrays['adc'],arrays['dwi'])


def test_failed_adc_only_policy_rejects_before_reading_input(tmp_path):
    import subprocess,sys
    from pathlib import Path
    script=Path(__file__).resolve().parents[1]/'scripts/predict_advanced_fusion.py'
    result=subprocess.run([sys.executable,str(script),'--adc',str(tmp_path/'nonexistent.nii.gz'),
                           '--output',str(tmp_path/'output')],capture_output=True,text=True)
    assert result.returncode==2 and 'DWI is required' in result.stderr
    assert not (tmp_path/'output').exists()
