import importlib.util
from pathlib import Path
import numpy as np
from PIL import Image
import pytest

spec=importlib.util.spec_from_file_location('audit_brisc',Path(__file__).parents[1]/'scripts/audit_brisc.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_decoded_hash_detects_identical_pixels_in_different_files(tmp_path):
    values=np.arange(64,dtype=np.uint8).reshape(8,8)
    a,b=tmp_path/'a.png',tmp_path/'b.png'
    Image.fromarray(values).save(a,compress_level=0)
    Image.fromarray(values).save(b,compress_level=9)
    ra,rb=module.inspect_image(a),module.inspect_image(b)
    assert ra['sha256']!=rb['sha256']
    assert ra['pixel_sha256']==rb['pixel_sha256']


def test_mask_rejects_nonbinary_and_corrupt_image(tmp_path):
    path=tmp_path/'mask.png'
    Image.fromarray(np.array([[0,255],[255,0]],dtype=np.uint8)).save(path)
    assert module.inspect_image(path,True)['foreground_pixels']==2
    Image.fromarray(np.array([[0,80],[255,0]],dtype=np.uint8)).save(path)
    with pytest.raises(ValueError,match='non-binary'):
        module.inspect_image(path,True)
    path.write_bytes(b'not an image')
    with pytest.raises(OSError):
        module.inspect_image(path)
