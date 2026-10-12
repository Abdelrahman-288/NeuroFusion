"""Recompute selected-threshold voxel counts directly from saved volumes."""
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1];out=root/'experiments/stroke-threshold-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
if (out/'verification.json').exists():raise ValueError('Verification exists')
summary=read(out/'summary.json');protocol=read(out/'protocol.json')
if digest(out/'protocol.json')!=summary['protocol_sha256']:raise ValueError('Protocol changed')
threshold=summary['selected_threshold']
if threshold is None:raise ValueError('No selected candidate')
records=read(out/f'cases-{threshold:.2f}.json')['voxel_cases']
saved={c['subject']:c for c in records}
run=root/protocol['candidate_run'];config=read(run/'config.json');proof=read(run/'checkpoint-reproduction.json')
manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
assert digest(manifest)==config['manifest_sha256'] and digest(splits)==config['splits_sha256']
assert proof['passed'] and digest(run/'last.pt')==proof['checkpoint_sha256']==protocol['checkpoint_sha256']
store=StudyStore(manifest,splits,root/'data/preprocessing-cache')
studies=store.studies('validation');hashes={r['case']:r['prediction_sha256'] for r in proof['cases']}
assert len(saved)==len(records)==len(studies) and set(saved)=={s['subject_id'] for s in studies}
for study in studies:
    subject=study['subject_id'];_,target,meta=store.load(study)
    path=run/'predictions'/f'{subject}-probability.nii.gz'
    assert digest(path)==hashes[subject]
    image=nib.as_closest_canonical(nib.load(path))
    assert image.shape==target.shape and np.allclose(image.affine,meta['canonical_affine'],atol=1e-4,rtol=0)
    assert image.header.get_xyzt_units()[0]==meta['xyzt_units'][0]
    values=image.get_fdata(dtype=np.float32)
    assert np.isfinite(values).all() and values.min()>=0 and values.max()<=1
    mask=values>=threshold;truth=target>0
    predicted=int(np.count_nonzero(mask));reference=int(np.count_nonzero(truth));tp=int(np.count_nonzero(mask[truth]))
    scale={'mm':1.,'meter':1000.,'micron':.001}[image.header.get_xyzt_units()[0]]
    voxel_ml=abs(np.linalg.det(image.affine[:3,:3]))*scale**3/1000
    expected={'predicted_voxels':predicted,'reference_voxels':reference,'false_positive_voxels':predicted-tp,
              'dice':2*tp/(predicted+reference) if predicted+reference else 1.,
              'false_positive_ml':(predicted-tp)*voxel_ml,'absolute_volume_error_ml':abs(predicted-reference)*voxel_ml}
    for name,value in expected.items():
        if not np.isclose(saved[subject][name],value,atol=1e-10,rtol=0):raise ValueError(f'{subject}: {name} mismatch')
save_json(out/'verification.json',{'passed':True,'case_count':len(studies),'threshold':threshold,
          'summary_sha256':digest(out/'summary.json'),'checkpoint_sha256':digest(run/'last.pt'),
          'script_sha256':digest(Path(__file__)),'scope':'Independent voxel-count recomputation; lesion matching uses the tested common evaluator',
          'holdout_loaded':False,'independently_qualified':False})
print('Verified all selected-threshold voxel metrics against saved volumes')
