"""Replay members, simulate missing inputs, and evaluate pre-recorded calibration."""
import hashlib
import json
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
from pathlib import Path
import nibabel as nib
import numpy as np
import torch
from neurofusion.advanced_fusion import SeparateEncoderUNet,modality_input,ensemble_probabilities,entropy,temperature_scale,reliability
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.fusion import load_fusion_study
from neurofusion.segmentation import CompactUNet,predict_volume,metrics
from neurofusion.preprocessing import restore_prediction
from neurofusion.lesions import lesion_metrics
from evaluate_lesions import totals

root=Path(__file__).resolve().parents[1];out=root/'experiments/advanced-fusion-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
protocol=read(out/'protocol.json')
if (out/'evaluation').exists():raise ValueError('Fresh evaluation directory required')
manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
assert digest(manifest)==protocol['manifest_sha256'] and digest(splits)==protocol['splits_sha256']
for name,sha in protocol['source_sha256'].items():
    if digest(root/name)!=sha:raise ValueError('Training source changed')
for name,sha in protocol['baseline_sha256'].items():
    if digest(root/'experiments'/name/'last.pt')!=sha:raise ValueError('Baseline changed')
store=StudyStore(manifest,splits,root/'data/preprocessing-cache')
studies=store.studies('validation')
assert set(protocol['calibration_fit_patients']).isdisjoint(protocol['calibration_evaluation_patients'])
assert set(protocol['calibration_fit_patients']+protocol['calibration_evaluation_patients'])=={s['subject_id'] for s in studies}
torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
models={};bindings={}
for name,model in [('dwi-component-001',CompactUNet()),('dwi-adc-002',CompactUNet(2)),('separate-encoder-001',SeparateEncoderUNet())]:
    path=root/'experiments'/name
    proof=read(path/'coverage-verification.json')
    assert proof['passed'] and proof['last_checkpoint_sha256']==digest(path/'last.pt')
    with torch.serialization.safe_globals([np._core.multiarray.scalar,np.dtype,type(np.dtype('float64'))]):
        checkpoint=torch.load(path/'last.pt',weights_only=True,map_location='cpu')
    assert checkpoint['epoch']==5
    assert checkpoint['config']['manifest_sha256']==protocol['manifest_sha256']
    assert checkpoint['config']['splits_sha256']==protocol['splits_sha256']
    model.load_state_dict(checkpoint['model']);models[name]=model.cuda().eval();bindings[name]=digest(path/'last.pt')
evaluation=out/'evaluation';evaluation.mkdir()
modes=('both','missing_adc','missing_dwi')
records={m:[] for m in modes};samples={m:[] for m in modes};lesions={m:[] for m in modes}
member_scores={name:[] for name in models};replays=[]
for index,study in enumerate(studies):
    subject=study['subject_id'];x,y,meta=load_fusion_study(store,study)
    p={}
    for name,model in models.items():
        inputs=x[0] if name=='dwi-component-001' else x if name=='dwi-adc-002' else modality_input(x[0],x[1])
        predicted=predict_volume(model,inputs,'cuda')
        path=root/'experiments'/name/'predictions'/f'{subject}-probability.nii.gz'
        image=nib.as_closest_canonical(nib.load(path));saved=image.get_fdata(dtype=np.float32)
        if saved.shape!=y.shape or not np.allclose(image.affine,meta['canonical_affine'],atol=1e-4,rtol=0):raise ValueError('Saved geometry differs')
        difference=float(np.max(np.abs(predicted-saved)))
        if difference>1e-6 or not np.array_equal(predicted>=.5,saved>=.5):raise ValueError('Checkpoint reproduction failed')
        replays.append({'subject':subject,'member':name,'max_difference':difference,'saved_prediction_sha256':digest(path)})
        p[name]=predicted;member_scores[name].append({'subject':subject,**metrics(predicted,y)})
    separate=models['separate-encoder-001']
    missing_adc=predict_volume(separate,modality_input(x[0],None),'cuda')
    missing_dwi=predict_volume(separate,modality_input(None,x[1]),'cuda')
    members={'both':list(p.values()),'missing_adc':[p['dwi-component-001'],missing_adc],'missing_dwi':[missing_dwi]}
    indices=np.flatnonzero(x[0].ravel()!=0)
    rng=np.random.default_rng(int(hashlib.sha256(('advanced-fusion-voxels:'+subject).encode()).hexdigest()[:16],16))
    indices=rng.choice(indices,size=min(4096,len(indices)),replace=False)
    scale={'mm':1.,'meter':1000.,'micron':.001}[meta['xyzt_units'][0]]
    voxel_ml=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))*scale**3/1000
    for mode,member_arrays in members.items():
        mean,variance=ensemble_probabilities(member_arrays);uncertainty=entropy(mean)
        score=metrics(mean,y)
        score.update(subject=subject,member_count=len(member_arrays),false_positive_ml=score['false_positive_voxels']*voxel_ml,
                     absolute_volume_error_ml=abs(score['predicted_voxels']-score['reference_voxels'])*voxel_ml,
                     raw_uncertainty=float(np.quantile(uncertainty.ravel()[indices],.9)))
        records[mode].append(score)
        lesion=lesion_metrics(mean,y,voxel_ml)
        lesions[mode].append({k:v for k,v in lesion.items() if not k.endswith('_details')})
        sample={'subject':subject,'p':mean.ravel()[indices],'y':y.ravel()[indices]}
        samples[mode].append(sample)
        folder=evaluation/mode/subject
        restore_prediction(mean,meta,folder/'probability.nii.gz')
        restore_prediction(uncertainty.astype(np.float32),meta,folder/'entropy.nii.gz')
        if len(member_arrays)>1:restore_prediction(variance,meta,folder/'disagreement.nii.gz')
        np.savez_compressed(folder/'calibration-sample.npz',probability=sample['p'],target=sample['y'],canonical_flat_indices=indices)
    print(f'Evaluated {index+1}/{len(studies)}: {subject}',flush=True)
results={}
for mode in modes:
    fitting=[s for s in samples[mode] if s['subject'] in protocol['calibration_fit_patients']]
    testing=[s for s in samples[mode] if s['subject'] in protocol['calibration_evaluation_patients']]
    losses={t:float(np.mean([reliability(temperature_scale(s['p'],t),s['y'])['nll'] for s in fitting])) for t in protocol['temperature_grid']}
    chosen=min(losses,key=lambda t:(losses[t],t!=1,t))
    calibration={}
    for label,t in [('raw',1),('calibrated',chosen)]:
        per_case=[{'subject':s['subject'],**reliability(temperature_scale(s['p'],t),s['y'])} for s in testing]
        calibration[label]={'mean':{k:float(np.mean([r[k] for r in per_case])) for k in ('nll','brier','ece')},'cases':per_case}
    fit_rows=[r for r in records[mode] if r['subject'] in protocol['calibration_fit_patients']]
    test_rows=[r for r in records[mode] if r['subject'] in protocol['calibration_evaluation_patients']]
    cutoff=float(np.quantile([r['raw_uncertainty'] for r in fit_rows],.8))
    accepted=[r for r in test_rows if r['raw_uncertainty']<=cutoff]
    all_risk=float(np.mean([1-r['dice'] for r in test_rows]))
    accepted_risk=float(np.mean([1-r['dice'] for r in accepted])) if accepted else None
    coverage=len(accepted)/len(test_rows)
    checks={k+'_not_higher':calibration['calibrated']['mean'][k]<=calibration['raw']['mean'][k] for k in ('nll','brier','ece')}
    checks.update(coverage_at_least_half=coverage>=.5,accepted_risk_not_higher=accepted_risk is not None and accepted_risk<=all_risk)
    results[mode]={'members':records[mode][0]['member_count'],'mean_dice':float(np.mean([r['dice'] for r in records[mode]])),
        'mean_absolute_volume_error_ml':float(np.mean([r['absolute_volume_error_ml'] for r in records[mode]])),
        'mean_false_positive_ml':float(np.mean([r['false_positive_ml'] for r in records[mode]])),
        'zero_dice_cases':sum(r['dice']==0 for r in records[mode]),'lesions':totals(lesions[mode]),'cases':records[mode],
        'temperature':chosen,'fitting_nll_grid':losses,'calibration':calibration,
        'abstention':{'cutoff_from_fitting':cutoff,'coverage':coverage,'all_case_risk':all_risk,'accepted_case_risk':accepted_risk,
                     'accepted':[r['subject'] for r in accepted],'abstained':[r['subject'] for r in test_rows if r not in accepted]},
        'development_checks':checks,'development_checks_passed':all(checks.values()),'independently_reliable':False}
summary={'protocol_sha256':digest(out/'protocol.json'),'checkpoint_sha256':bindings,'modes':results,
         'member_mean_dice':{k:float(np.mean([r['dice'] for r in v])) for k,v in member_scores.items()},
         'member_cases':member_scores,'reproduction_count':len(replays),'holdout_used':False,'ucsf_used':False,
         'production_models_changed':False,'independent_uncertainty_reliability_established':False,
         'source_sha256':digest(Path(__file__))}
save_json(out/'checkpoint-reproduction.json',{'passed':True,'records':replays,'checkpoint_sha256':bindings})
save_json(out/'summary.json',summary)
print(json.dumps({k:{'dice':v['mean_dice'],'checks':v['development_checks']} for k,v in results.items()},indent=2))
