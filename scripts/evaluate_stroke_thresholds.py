"""Fixed exploratory development threshold grid; never promotes a model."""
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore, digest
from neurofusion.data import save_json
from neurofusion.lesions import lesion_metrics
from neurofusion.segmentation import metrics
from neurofusion.model_quality import compare_stroke
from evaluate_lesions import totals

root=Path(__file__).resolve().parents[1]
out=root/'experiments/stroke-threshold-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
protocol=read(out/'protocol.json')
if (out/'summary.json').exists():raise ValueError('Results already exist')
run=root/protocol['candidate_run'];baseline=root/protocol['baseline_run']
proof=read(run/'checkpoint-reproduction.json');config=read(run/'config.json')
if not proof['passed'] or digest(run/'last.pt')!=protocol['checkpoint_sha256'] or proof['checkpoint_sha256']!=protocol['checkpoint_sha256']:
    raise ValueError('Checkpoint reproduction mismatch')
if digest(root/'experiments/model-quality-001/protocol.json')!=protocol['checks_source_sha256']:
    raise ValueError('Original checks changed')
manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
if digest(manifest)!=config['manifest_sha256'] or digest(splits)!=config['splits_sha256']:raise ValueError('Dataset binding changed')
store=StudyStore(manifest,splits,root/'data/preprocessing-cache')
studies=store.studies('validation')
if sorted(s['subject_id'] for s in studies)!=sorted(config['validation_subjects']):raise ValueError('Case set differs')
hashes={c['case']:c['prediction_sha256'] for c in proof['cases']}
base=read(baseline/'summary.json')['final_validation']['cases']
for case in base:
    image=nib.load(baseline/'predictions'/f'{case["subject"]}-probability.nii.gz')
    scale={'mm':1.,'meter':1000.,'micron':.001}[image.header.get_xyzt_units()[0]]
    case['false_positive_ml']=case['false_positive_voxels']*abs(np.linalg.det(image.affine[:3,:3]))*scale**3/1000
base_lesions=read(root/'experiments/lesion-analysis-component-001/summary.json')['primary']
rows={t:[] for t in protocol['thresholds']};lesions={t:[] for t in rows}
for i,study in enumerate(studies):
    subject=study['subject_id'];_,target,meta=store.load(study)
    path=run/'predictions'/f'{subject}-probability.nii.gz'
    if digest(path)!=hashes[subject]:raise ValueError('Prediction changed')
    image=nib.as_closest_canonical(nib.load(path))
    if image.shape!=target.shape or not np.allclose(image.affine,meta['canonical_affine'],rtol=0,atol=1e-4) or image.header.get_xyzt_units()[0]!=meta['xyzt_units'][0]:raise ValueError('Geometry mismatch')
    probability=image.get_fdata(dtype=np.float32)
    scale={'mm':1.,'meter':1000.,'micron':.001}[image.header.get_xyzt_units()[0]]
    voxel_ml=abs(np.linalg.det(image.affine[:3,:3]))*scale**3/1000
    for threshold in rows:
        values=metrics(probability,target,threshold)
        values.update(subject=subject,false_positive_ml=values['false_positive_voxels']*voxel_ml,
                      absolute_volume_error_ml=abs(values['predicted_voxels']-values['reference_voxels'])*voxel_ml)
        rows[threshold].append(values)
        details=lesion_metrics(probability,target,voxel_ml,threshold=threshold)
        lesions[threshold].append({k:v for k,v in details.items() if not k.endswith('_details')})
    print(f'Checked {i+1}/{len(studies)}',flush=True)
results=[]
for threshold in rows:
    result=compare_stroke(base,rows[threshold],base_lesions,totals(lesions[threshold]))
    results.append({'threshold':threshold,**result})
    save_json(out/f'cases-{threshold:.2f}.json',{'voxel_cases':rows[threshold],'lesion_cases':lesions[threshold]})
passed=[r for r in results if r['development_screen_passed']]
selected=sorted(passed,key=lambda r:(-r['candidate']['mean_dice'],r['threshold']))[0]['threshold'] if passed else None
summary={'results':results,'selected_threshold':selected,'protocol_sha256':digest(out/'protocol.json'),
         'checkpoint_sha256':protocol['checkpoint_sha256'],'script_sha256':digest(Path(__file__)),
         'holdout_evaluated':False,'independently_qualified':False,'promotion_permitted':False,
         'note':'Exploratory threshold selection on reused development data. Original threshold-0.5 failure remains unchanged.'}
save_json(out/'summary.json',summary)
print(json.dumps({'selected_threshold':selected,'checks':{r['threshold']:r['checks'] for r in results}}))
