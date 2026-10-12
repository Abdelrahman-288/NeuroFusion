"""Compare the prespecified UCSF sampling experiment against its baseline."""
import json,hashlib,argparse
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.ucsf_sampling import compare_runs
from neurofusion.native_metrics import native_binary_metrics
from neurofusion.specialist_plan import numeric_foreground

parser=argparse.ArgumentParser();parser.add_argument('--low-lr',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parents[1];baseline=root/'experiments/ucsf-specialist-train-002';candidate=root/('experiments/ucsf-low-lr-train-001' if args.low_lr else 'experiments/ucsf-balanced-train-001');out=root/('experiments/ucsf-low-lr-comparison-001' if args.low_lr else 'experiments/ucsf-balanced-comparison-001')
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
experiment_name='experiment-protocol.json' if args.low_lr else 'sampling-protocol.json'
if args.low_lr:
    control=read(baseline/'protocol.json');changed=read(candidate/'protocol.json')
    if changed['training_plan']['learning_rate']!=.0003:raise ValueError('Wrong learning rate')
    changed['training_plan']['learning_rate']=.001
    if changed!=control:raise ValueError('More than learning rate changed')
for name in (('partitions.json','cache-manifest.json') if args.low_lr else ('protocol.json','partitions.json','cache-manifest.json')):
    if sha(baseline/name)!=sha(candidate/name):raise ValueError('Controls differ: '+name)
for name in ('tumor_segmentation.py','external_adapter.py','native_metrics.py','ucsf_validation.py','ucsf_loader.py'):
    if sha(baseline/'source'/name)!=sha(candidate/'source'/name):raise ValueError('Shared implementation changed: '+name)
b,c=read(baseline/'summary.json'),read(candidate/'summary.json')
parts=read(candidate/'partitions.json');verified=[]
for name,checksum in c['checkpoints'].items():
    if sha(candidate/name)!=checksum:raise ValueError('Checkpoint mismatch')
for case in c['final_epoch']['cases']:
    row=next(r for r in parts['records'] if r['exam_id']==case['exam_id'])
    path=root/'data/raw/ucsf-pdgm-v5'/row['mask']['path']
    if sha(path)!=row['mask']['sha256']:raise ValueError('Reference changed')
    reference=nib.load(path);truth=nib.Nifti1Image(numeric_foreground(reference.get_fdata()).astype(np.uint8),reference.affine,reference.header.copy())
    prediction=nib.load(candidate/(case['exam_id']+'-prediction.nii.gz'))
    if native_binary_metrics(prediction,truth)!=case['metrics']:raise ValueError('Saved prediction metrics mismatch')
    verified.append(case['exam_id'])
result=compare_runs(b,c);history=read(candidate/'history.json')
if args.low_lr:
    result['decision']='paired-seed confirmation candidate' if result['all_passed'] else 'retain baseline; lower-learning-rate candidate rejected'
    if any(h['unique_slice_draws']!=2480 or h['positive_draws']!=1015 for h in history):raise ValueError('Uniform complete training coverage changed')
    result['epoch_dice']=[h['aggregate']['dice']['mean'] for h in history]
    result['final_minus_penultimate_dice']=result['epoch_dice'][-1]-result['epoch_dice'][-2]
result.update({'baseline':str(baseline.relative_to(root)),'candidate':str(candidate.relative_to(root)),'saved_prediction_metrics_verified':verified,'positive_draws_by_epoch':[r['positive_draws'] for r in history],'unique_slices_by_epoch':[r['unique_slice_draws'] for r in history],'overflow_skipped_updates':sum(r['overflow_skipped_updates'] for r in history),'controls_verified':['protocol','partition','cache manifest','shared model/preprocessing/metrics source'],'limitations':['Four development patients, already reviewed; no independent test cohort','Single seed; no generalization or clinical readiness claim','Five epochs at a lower learning rate may converge more slowly' if args.low_lr else 'Sampling with replacement changes repeat exposure and per-epoch unique coverage as specified']})
out.mkdir(exist_ok=False)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(out/'protocol.json').write_bytes(candidate.joinpath(experiment_name).read_bytes())
(out/'provenance.json').write_text(json.dumps({str(p.relative_to(root)):sha(p) for p in [Path(__file__),root/'src/neurofusion/ucsf_sampling.py',baseline/'summary.json',candidate/'summary.json',candidate/experiment_name]},indent=2),encoding='utf-8')
rows=''.join(f'<tr><td>{r["patient_id"]}</td><td>{r["baseline_dice"]:.4f}</td><td>{r["candidate_dice"]:.4f}</td><td>{r["dice_delta"]:+.4f}</td><td>{r["baseline_fp_ml"]:.3f}</td><td>{r["candidate_fp_ml"]:.3f}</td></tr>' for r in result['patients'])
gates=''.join(f'<li>{name.replace("_"," ")}: <strong>{"PASS" if passed else "FAIL"}</strong></li>' for name,passed in result['gates'].items())
means=result['means']
page=('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UCSF sampling comparison</title><style>body{font:17px system-ui;background:#101b2b;color:#ecf3fb;max-width:1100px;margin:30px auto;padding:20px}td,th{padding:12px;border-bottom:1px solid #456;text-align:left}a{color:#80ded0}table{border-collapse:collapse}section{overflow:auto}strong{color:#ffc467}</style><h1>Balanced foreground sampling</h1><p>Five epochs, seed 42, identical patient split and model. Training uses 50/50 positive/empty slice probability with replacement; full validation volumes are unchanged.</p>'''+f'<h2>{result["decision"]}</h2><p>Mean Dice: {means["baseline_dice"]:.4f} → {means["candidate_dice"]:.4f}. Mean IoU: {means["baseline_iou"]:.4f} → {means["candidate_iou"]:.4f}. Mean extra-prediction volume: {means["baseline_fp_ml"]:.3f} → {means["candidate_fp_ml"]:.3f} mL.</p><ul>'+gates+'</ul><section><table><tr><th>Patient</th><th>Baseline Dice</th><th>Balanced Dice</th><th>Change</th><th>Baseline FP mL</th><th>Balanced FP mL</th></tr>'+rows+'</table></section><p>Final epoch selected in advance. Four repeatedly reviewed development patients; no independent test set. No model promoted and no clinical claim. A pass qualifies only for paired-seed confirmation.</p><p><a href="summary.json">Full comparison</a> · <a href="protocol.json">Predefined experiment rules</a> · <a href="provenance.json">Provenance</a></p></html>')
if args.low_lr:
    page=page.replace('UCSF sampling comparison','UCSF learning-rate comparison').replace('Balanced foreground sampling','Lower learning rate').replace('Training uses 50/50 positive/empty slice probability with replacement; full validation volumes are unchanged.','Adam learning rate changes from 0.001 to 0.0003. Original uniform sampling and full validation volumes are unchanged.').replace('Balanced Dice','Lower-LR Dice').replace('Balanced FP mL','Lower-LR FP mL')
(out/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(result,indent=2))
