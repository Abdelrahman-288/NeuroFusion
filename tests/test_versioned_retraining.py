import copy,json,zipfile
from pathlib import Path
import nibabel as nib
import numpy as np
from PIL import Image
import pytest
import torch
from neurofusion.annotation_versions import binding,validate_version,apply_approved_export
from neurofusion.retraining import train,assemble,load_case
from neurofusion.model_registry import promote
from neurofusion.tumor import TumorCNN
from neurofusion.tumor_segmentation import TumorUNet
from neurofusion.segmentation import CompactUNet


def version(root,key):
    records=[]
    for role in ('train','validation'):
        if key=='stroke_dwi':
            x=np.arange(16**3,dtype=np.float32).reshape(16,16,16);y=(x>3000).astype(np.uint8)
            for name,array in [('image',x),('mask',y)]:
                image=nib.Nifti1Image(array,np.diag([2,2,2,1]));image.header.set_xyzt_units('mm');nib.save(image,root/f'{role}-{name}.nii')
            image=root/f'{role}-image.nii';mask=root/f'{role}-mask.nii'
        else:
            image=root/f'{role}.png';mask=root/f'{role}-mask.png'
            Image.fromarray(np.arange(32**2,dtype=np.uint8).reshape(32,32)).save(image)
            y=np.zeros((32,32),dtype=np.uint8);y[8:16,8:16]=255;Image.fromarray(y).save(mask)
        r=dict(id=role,group=role,partition=role,image=binding(root,image),class_label='glioma')
        if key!='tumor_classifier':r['mask']=binding(root,mask)
        records.append(r)
    (root/'source.json').write_text('{}')
    value=dict(schema_version=1,model_key=key,records=records,source_bindings=[binding(root,root/'source.json')],protected_data_used=False)
    path=root/'annotations.json';path.write_text(json.dumps(value));return path,value


@pytest.mark.parametrize('key',['tumor_classifier','tumor_segmenter','stroke_dwi'])
def test_train_to_acceptance_rejects_missing_gates(tmp_path,monkeypatch,key):
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    path,v=version(tmp_path,key)
    model={'tumor_classifier':TumorCNN,'tumor_segmenter':TumorUNet,'stroke_dwi':CompactUNet}[key]()
    torch.save(dict(model=model.state_dict()),tmp_path/'base.pt')
    b=binding(tmp_path,tmp_path/'base.pt');defaults={key:(b['path'],b['sha256'])}
    monkeypatch.setattr('neurofusion.retraining.MODELS',defaults)
    run=train(tmp_path,path,tmp_path/'run')
    result=json.loads(run.read_text());assert result['training_cases']==1 and result['validation_cases']==1
    assert result['replay_max_difference']==0
    report=assemble(tmp_path,run,tmp_path/'decision')
    decision=json.loads((report.parent/'decision.json').read_text())
    assert not decision['eligible'] and 'independent_evaluation' in decision['failed_or_missing']
    with pytest.raises(ValueError,match='check must pass'):promote(tmp_path,defaults,report.relative_to(tmp_path).as_posix(),-1)
    assert not (tmp_path/'configs/model_registry.json').exists()
    gate=dict(gate='robustness',model_key=key,checkpoint_sha256=result['checkpoint']['sha256'],
        annotation_version=result['annotation_version'],protocol=result['protocol'],passed=True,artifacts=[result['validation']])
    gatepath=tmp_path/'gate.json';gatepath.write_text(json.dumps(gate))
    supplemented=assemble(tmp_path,run,tmp_path/'supplemented',{'robustness':gatepath})
    assert json.loads(supplemented.read_text())['checks']['robustness'] is True
    gate['checkpoint_sha256']='0'*64;gatepath.write_text(json.dumps(gate))
    with pytest.raises(ValueError,match='binding'):assemble(tmp_path,run,tmp_path/'stale',{'robustness':gatepath})
    with pytest.raises(FileExistsError):train(tmp_path,path,tmp_path/'run')


def test_annotation_mutation_and_partition_crossing(tmp_path):
    path,v=version(tmp_path,'tumor_segmenter');b=binding(tmp_path,path)
    assert len(validate_version(tmp_path,b)['records'])==2
    bad=copy.deepcopy(v);bad['records'][1]['group']='train';path.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='checksum'):validate_version(tmp_path,b)
    with pytest.raises(ValueError,match='cross'):validate_version(tmp_path,binding(tmp_path,path))
    path.write_text(json.dumps(v));(tmp_path/'train-mask.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):validate_version(tmp_path,binding(tmp_path,path))


def test_approved_export_cannot_move_validation_to_train(tmp_path):
    path,v=version(tmp_path,'stroke_dwi');r=v['records'][1]
    # Unique input content prevents deliberately ambiguous test-source hashes.
    r['image']['sha256']='c'*64
    manifest=dict(records=[dict(adjudication=dict(decision='approve',whole_volume_reviewed=True,image_sha256='c'*64))])
    export=tmp_path/'approved.zip'
    with zipfile.ZipFile(export,'w') as z:z.writestr('manifest.json',json.dumps(manifest))
    with pytest.raises(ValueError,match='training case'):apply_approved_export(tmp_path,tmp_path,v['records'],export)


def test_approved_binary_mask_import_and_geometry_check(tmp_path):
    import hashlib
    _,v=version(tmp_path,'stroke_dwi');r=v['records'][0]
    v['records'][1]['image']['sha256']='c'*64
    data=(tmp_path/'train-mask.nii').read_bytes();sha=hashlib.sha256(data).hexdigest()
    item=dict(adjudication=dict(decision='approve',whole_volume_reviewed=True,image_sha256=r['image']['sha256'],mask_sha256=sha),
        source_files=[r['image']],label_path='labels/corrected.nii',label_sha256=sha)
    export=tmp_path/'approved.zip'
    with zipfile.ZipFile(export,'w') as z:z.writestr('manifest.json',json.dumps(dict(records=[item])));z.writestr(item['label_path'],data)
    assert apply_approved_export(tmp_path,tmp_path,v['records'],export)==1
    assert r['annotation_origin']=='approved_export'
    x,y,_=load_case(tmp_path,'stroke_dwi',r);assert x.shape==y.shape
    bad=nib.Nifti1Image(np.ones((16,16,16),dtype=np.uint8),np.diag([3,3,3,1]));bad.header.set_xyzt_units('mm');nib.save(bad,tmp_path/'bad.nii')
    r['mask']=binding(tmp_path,tmp_path/'bad.nii')
    with pytest.raises(ValueError,match='grid'):load_case(tmp_path,'stroke_dwi',r)
