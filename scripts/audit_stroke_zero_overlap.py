"""Recheck .65 and evaluate one fixed lower-threshold/small-component correction."""
import argparse
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.segmentation import metrics
from neurofusion.lesions import lesion_metrics
from neurofusion.model_quality import compare_stroke
from neurofusion.stroke_postprocessing import threshold_components
from evaluate_lesions import totals

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
candidate=root/'experiments/dwi-continuation-002';baseline=root/'experiments/dwi-component-001'
read=lambda path:json.loads(path.read_text())
config=read(candidate/'config.json');proof=read(candidate/'checkpoint-reproduction.json')
manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
if not proof['passed'] or digest(candidate/'last.pt')!=proof['checkpoint_sha256']:raise ValueError('Candidate binding changed')
if digest(manifest)!=config['manifest_sha256'] or digest(splits)!=config['splits_sha256']:raise ValueError('Data changed')
protocol=dict(candidate_sha256=proof['checkpoint_sha256'],baseline_sha256=digest(baseline/'last.pt'),
    manifest_sha256=digest(manifest),splits_sha256=digest(splits),partition='validation',
    arms={'baseline':{'threshold':.5},'selected':{'threshold':.65},'correction':{'threshold':.55,'minimum_component_ml':.01,'connectivity':26}},
    rationale='Lower threshold recovers weak overlap; remove components smaller than 0.01 mL to target excess tiny false positives. One fixed correction; may also remove true small lesions.',
    acceptance='Original six relative checks plus zero-Dice count not higher AND no newly zero-Dice patient relative to baseline',
    same_patient_confirmation_only=True,additional_seed_confirmation=False,
    limitation='Exploratory reused development cohort; not independent or cross-seed confirmation',
    holdout_evaluated=False,promotion_permitted=False,script_sha256=digest(Path(__file__)),
    postprocess_sha256=digest(root/'src/neurofusion/stroke_postprocessing.py'))
save_json(a.output/'protocol.json',protocol)
store=StudyStore(manifest,splits,root/'data/preprocessing-cache');studies=store.studies('validation')
if sorted(s['subject_id'] for s in studies)!=sorted(config['validation_subjects']):raise ValueError('Coverage differs')
hashes={c['case']:c['prediction_sha256'] for c in proof['cases']}
base_proof=read(baseline/'coverage-verification.json')
if digest(baseline/'last.pt')!=base_proof['last_checkpoint_sha256'] or not base_proof['passed']:raise ValueError('Baseline binding changed')
rows={key:[] for key in protocol['arms']};lesions={key:[] for key in rows};diagnostics=[];sources=[]
for index,study in enumerate(studies):
    subject=study['subject_id'];_,truth,meta=store.load(study)
    probabilities={}
    for key,folder in [('baseline',baseline),('candidate',candidate)]:
        path=folder/'predictions'/f'{subject}-probability.nii.gz'
        checksum=digest(path)
        if key=='candidate' and checksum!=hashes[subject]:raise ValueError('Prediction changed')
        image=nib.as_closest_canonical(nib.load(path))
        if image.shape!=truth.shape or image.header.get_xyzt_units()[0]!='mm' or not np.allclose(image.affine,meta['canonical_affine'],atol=1e-4,rtol=0):raise ValueError('Geometry changed')
        probabilities[key]=image.get_fdata(dtype=np.float32)
        sources.append(dict(subject=subject,role=key,path=str(path.relative_to(root)),sha256=checksum))
    voxel_ml=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))/1000
    masks=dict(baseline=probabilities['baseline']>=.5,selected=probabilities['candidate']>=.65,
               correction=threshold_components(probabilities['candidate'],voxel_ml))
    for key,mask in masks.items():
        m=metrics(mask.astype(float),truth,.5)
        m.update(subject=subject,false_positive_ml=m['false_positive_voxels']*voxel_ml,
                 absolute_volume_error_ml=abs(m['predicted_voxels']-m['reference_voxels'])*voxel_ml)
        rows[key].append(m)
        detail=lesion_metrics(mask.astype(float),truth,voxel_ml)
        lesions[key].append({k:v for k,v in detail.items() if not k.endswith('_details')})
    if any(rows[key][-1]['dice']==0 for key in rows):
        diagnostics.append(dict(subject=subject,reference_ml=float(truth.sum()*voxel_ml),
            candidate_max_probability_in_reference=float(probabilities['candidate'][truth>0].max()),
            reference_voxels_above_055=int(((probabilities['candidate']>=.55)&(truth>0)).sum()),
            reference_voxels_above_065=int(((probabilities['candidate']>=.65)&(truth>0)).sum()),
            dice={key:rows[key][-1]['dice'] for key in rows}))
    print(f'Checked {index+1}/{len(studies)}',flush=True)
base_zero={r['subject'] for r in rows['baseline'] if r['dice']==0}
results={}
for key in ('selected','correction'):
    result=compare_stroke(rows['baseline'],rows[key],totals(lesions['baseline']),totals(lesions[key]))
    zero={r['subject'] for r in rows[key] if r['dice']==0}
    result['newly_zero_dice_patients']=sorted(zero-base_zero)
    result['recovered_patients']=sorted(base_zero-zero)
    result['checks'].update(zero_dice_count_not_higher=len(zero)<=len(base_zero),no_new_zero_dice_patients=not bool(zero-base_zero))
    result['expanded_checks_passed']=all(result['checks'].values())
    results[key]=result
save_json(a.output/'cases.json',dict(voxel=rows,lesion=lesions))
save_json(a.output/'zero-overlap-diagnostics.json',diagnostics)
save_json(a.output/'source-hashes.json',sources)
summary=dict(results=results,threshold_065_confirmed=results['selected']['expanded_checks_passed'],
    correction_passed=results['correction']['expanded_checks_passed'],
    independent_confirmation=False,cross_seed_confirmation=False,promotion_permitted=False,
    holdout_evaluated=False,protocol_sha256=digest(a.output/'protocol.json'))
save_json(a.output/'summary.json',summary)
print(json.dumps(summary,indent=2))
