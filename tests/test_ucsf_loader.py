import hashlib
import json
import numpy as np
import pytest
from neurofusion.ucsf_loader import UCSFSlices


def fixture_cache(tmp_path):
    d=tmp_path/'case';d.mkdir()
    np.save(d/'images.npy',np.full((2,1,240,240),255,dtype=np.uint8))
    y=np.zeros((2,1,240,240),dtype=np.uint8);y[1,0,3,7]=1;np.save(d/'targets.npy',y)
    (d/'geometry.json').write_text('{}')
    row={'patient_id':'p','exam_id':'e','role':'train','directory':'case','slices':2,
         'sha256':{n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in ('images.npy','targets.npy','geometry.json')}}
    (tmp_path/'manifest.json').write_text(json.dumps({'cases':[row]}))
    return row


def test_empty_slice_retained_and_values_scaled(tmp_path):
    fixture_cache(tmp_path);d=UCSFSlices(tmp_path,'train')
    assert len(d)==2 and d[0]['image'].min()==1 and d[0]['target'].sum()==0
    assert d[1]['target'].sum()==1 and d[1]['canonical_z']==1


def test_changed_cache_rejected(tmp_path):
    fixture_cache(tmp_path);(tmp_path/'case/geometry.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='checksum'):UCSFSlices(tmp_path,'train')


def test_cross_patient_roles_and_unknown_role_rejected(tmp_path):
    row=fixture_cache(tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps({'cases':[row,{**row,'role':'development_validation'}]}))
    with pytest.raises(ValueError,match='crosses'):UCSFSlices(tmp_path,'train')
    with pytest.raises(ValueError,match='Only'):UCSFSlices(tmp_path,'test')
