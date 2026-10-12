"""Verify saved outputs, case sets and independently recomputed voxel counts."""
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
root=Path(__file__).resolve().parents[1];out=root/'experiments/advanced-fusion-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
summary=read(out/'summary.json');protocol=read(out/'protocol.json')
if (out/'verification.json').exists():raise ValueError('Verification exists')
assert summary['protocol_sha256']==digest(out/'protocol.json')
store=StudyStore(root/'experiments/isles-curated-001/manifest.json',root/'experiments/isles-curated-001/frozen-splits-v1.json',root/'data/preprocessing-cache')
files=[];count=0
for study in store.studies('validation'):
    subject=study['subject_id'];_,truth,meta=store.load(study)
    for mode,report in summary['modes'].items():
        folder=out/'evaluation'/mode/subject
        values={}
        names=['probability','entropy']+(['disagreement'] if report['members']>1 else [])
        if report['members']==1:assert not (folder/'disagreement.nii.gz').exists()
        for name in names:
            p=folder/(name+'.nii.gz');image=nib.as_closest_canonical(nib.load(p))
            assert image.shape==truth.shape and np.allclose(image.affine,meta['canonical_affine'],rtol=0,atol=1e-4)
            assert image.header.get_xyzt_units()[0]==meta['xyzt_units'][0]
            values[name]=image.get_fdata(dtype=np.float32)
            assert np.isfinite(values[name]).all() and values[name].min()>=0
            files.append({'path':p.relative_to(out).as_posix(),'sha256':digest(p)})
        assert values['probability'].max()<=1 and values['entropy'].max()<=np.log(2)+1e-6
        if report['members']>1:assert values['disagreement'].max()<=.25+1e-6
        p=values['probability'];prediction=p>=.5;target=truth>0
        tp=int(np.count_nonzero(prediction&target));n=int(prediction.sum());m=int(target.sum())
        row=next(r for r in report['cases'] if r['subject']==subject)
        assert row['predicted_voxels']==n and row['reference_voxels']==m and row['false_positive_voxels']==n-tp
        assert abs(row['dice']-(2*tp/(n+m) if n+m else 1))<1e-10
        sample=np.load(folder/'calibration-sample.npz',allow_pickle=False)
        assert np.array_equal(sample['probability'],p.ravel()[sample['canonical_flat_indices']])
        assert np.array_equal(sample['target'],truth.ravel()[sample['canonical_flat_indices']])
        count+=1
for mode,r in summary['modes'].items():
    ids=[c['subject'] for c in r['cases']];assert len(ids)==37 and len(set(ids))==37
    a=r['abstention'];assert set(a['accepted']).isdisjoint(a['abstained'])
    assert set(a['accepted']+a['abstained'])==set(protocol['calibration_evaluation_patients'])
    assert abs(a['coverage']-len(a['accepted'])/19)<1e-12
    assert r['independently_reliable'] is False
save_json(out/'verification.json',{'passed':True,'native_outputs_checked':count,'files':files,'summary_sha256':digest(out/'summary.json'),
    'script_sha256':digest(Path(__file__)),'holdout_used':False,'independent_reliability_established':False})
print(f'Verified {count} native-grid outputs and saved calibration samples')
