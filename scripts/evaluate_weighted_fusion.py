"""Fit conservative fusion weights on 18 existing development patients only."""
import argparse,json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.segmentation import metrics
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
read=lambda p:json.loads(p.read_text())
old=root/'experiments/advanced-fusion-001';prior=read(old/'protocol.json');report=read(old/'summary.json')
fit=set(prior['calibration_fit_patients']);evaluation=set(prior['calibration_evaluation_patients'])
if fit&evaluation:raise ValueError('Fitting/evaluation overlap')
weights=[0.,.1,.25,.5,1.]
protocol=dict(weights=weights,formula='(1-w)*DWI + w*(early_fusion+separate_encoder)/2',
    fitting_patients=sorted(fit),evaluation_patients=sorted(evaluation),
    selection='Among positive weights with strictly improved mean Dice, nonincreased FP and volume error, and no new zero-Dice patient in fitting, maximize mean Dice; otherwise DWI identity fallback',
    evaluation_checks='Same four checks on separate development patients; no promotion on failure',
    limitation='Reused development data; not independent evaluation or cross-seed confirmation',
    checkpoint_sha256=report['checkpoint_sha256'],holdout_used=False,threshold=.5)
save_json(a.output/'protocol.json',protocol)
proof=read(old/'checkpoint-reproduction.json')
hashes={(r['member'],r['subject']):r['saved_prediction_sha256'] for r in proof['records']}
store=StudyStore(root/'experiments/isles-curated-001/manifest.json',root/'experiments/isles-curated-001/frozen-splits-v1.json',root/'data/preprocessing-cache')
studies=store.studies('validation')
if {s['subject_id'] for s in studies}!=fit|evaluation:raise ValueError('Coverage differs')
rows={str(w):[] for w in weights}
for study in studies:
    subject=study['subject_id'];_,truth,meta=store.load(study);members=[]
    for name in ('dwi-component-001','dwi-adc-002','separate-encoder-001'):
        path=root/'experiments'/name/'predictions'/f'{subject}-probability.nii.gz'
        if digest(path)!=hashes[(name,subject)] or digest(root/'experiments'/name/'last.pt')!=report['checkpoint_sha256'][name]:raise ValueError('Model/prediction binding changed')
        image=nib.as_closest_canonical(nib.load(path))
        if image.shape!=truth.shape or image.header.get_xyzt_units()[0]!='mm' or not np.allclose(image.affine,meta['canonical_affine'],rtol=0,atol=1e-4):raise ValueError('Geometry differs')
        members.append(image.get_fdata(dtype=np.float32))
    voxel_ml=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))/1000
    for w in weights:
        prob=members[0] if w==0 else (1-w)*members[0]+w*(members[1]+members[2])/2
        score=metrics(prob,truth,.5)
        rows[str(w)].append(dict(subject=subject,dice=score['dice'],fp_ml=score['false_positive_voxels']*voxel_ml,
            volume_error_ml=abs(score['predicted_voxels']-score['reference_voxels'])*voxel_ml))
    print('Scored '+subject,flush=True)
def comparison(w,patients):
    baseline={r['subject']:r for r in rows['0.0'] if r['subject'] in patients}
    chosen=[r for r in rows[str(w)] if r['subject'] in patients]
    means={k:float(np.mean([r[k] for r in chosen])) for k in ('dice','fp_ml','volume_error_ml')}
    base={k:float(np.mean([r[k] for r in baseline.values()])) for k in means}
    new=[r['subject'] for r in chosen if r['dice']==0 and baseline[r['subject']]['dice']>0]
    checks=dict(dice_improves=means['dice']>base['dice'],fp_not_higher=means['fp_ml']<=base['fp_ml'],
        volume_error_not_higher=means['volume_error_ml']<=base['volume_error_ml'],no_new_zero_dice=not new)
    return dict(weight=w,baseline=base,candidate=means,checks=checks,passed=all(checks.values()),newly_zero_dice=new)
fitting=[comparison(w,fit) for w in weights if w>0]
eligible=[r for r in fitting if r['passed']]
chosen=max(eligible,key=lambda r:(r['candidate']['dice'],-r['weight']))['weight'] if eligible else 0.
save_json(a.output/'selection.json',dict(fitting=fitting,selected_weight=chosen))
result=comparison(chosen,evaluation)
save_json(a.output/'cases.json',rows)
save_json(a.output/'summary.json',dict(selected_weight=chosen,identity_fallback=chosen==0,
    evaluation=result,independently_qualified=False,promotion_permitted=False,
    recommendation='retain DWI baseline until a fusion candidate passes all qualification checks'))
print(json.dumps(dict(fitting=fitting,selected_weight=chosen,evaluation=result),indent=2))
