"""Evaluate the completed clipping probe on the fixed eight original volumes."""
from pathlib import Path
import json,hashlib
import torch,numpy as np,nibabel as nib
from neurofusion.tumor_segmentation import TumorUNet
from neurofusion.ucsf_validation import score_native
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-gradient-clip-probe-002'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=read(out/'summary.json');provenance=read(out/'provenance.json')
if sha(out/'epoch-05.pt')!=provenance['final_checkpoint_sha256']:raise ValueError('Checkpoint mismatch')
cache=root/'experiments/ucsf-specialist-cache-001';manifest=read(cache/'manifest.json');parts=read(root/'experiments/ucsf-specialist-plan-001/partitions.json')
selected=read(root/'experiments/ucsf-training-diagnostics-001/protocol.json')['training_patients']
control=next(r for r in read(root/'experiments/ucsf-training-diagnostics-001/results.json') if r['seed']==43 and r['mode']=='baseline' and r['epoch']==5)
model=TumorUNet().cuda();model.load_state_dict(torch.load(out/'epoch-05.pt',map_location='cpu',weights_only=False)['model_state_dict']);model.eval();cases=[]
with torch.inference_mode():
 for case in manifest['cases']:
  if case['role']=='train' and case['exam_id'] not in selected:continue
  directory=cache/case['directory']
  for name,checksum in case['sha256'].items():
   if sha(directory/name)!=checksum:raise ValueError('Cache mismatch')
  x=np.load(directory/'images.npy',mmap_mode='r');probs=[]
  for z in range(0,len(x),8):
   with torch.autocast('cuda',dtype=torch.float16):logits=model(torch.from_numpy(x[z:z+8].astype(np.float32)/255).cuda())
   probs.append(logits.float().sigmoid().cpu().numpy()[:,0])
  row=next(r for r in parts['records'] if r['exam_id']==case['exam_id']);source=root/'data/raw/ucsf-pdgm-v5'/row['mask']['path']
  if sha(source)!=row['mask']['sha256']:raise ValueError('Reference mismatch')
  metrics,pred=score_native(np.concatenate(probs),read(directory/'geometry.json'),nib.load(source));nib.save(pred,out/(case['exam_id']+'-prediction.nii.gz'))
  cases.append({'exam_id':case['exam_id'],'role':case['role'],'metrics':metrics})
groups={}
for role in ('train','development_validation'):
 cs=[c for c in cases if c['role']==role]
 groups[role]={'patients':len(cs),'mean_dice':float(np.mean([c['metrics']['dice'] for c in cs])),'mean_fp_ml':float(np.mean([c['metrics']['fp']*c['metrics']['voxel_ml'] for c in cs])),'empty_predictions':sum(c['metrics']['empty_state']=='prediction_empty' for c in cs)}
result={'purpose':'amended post hoc clipping intervention, not full retraining or clinical validation','groups':groups,'control_groups':control['groups'],'cases':cases,'initial_attempt':'aborted at update 244 under fail-on-nonfinite policy','amendment':'retain original AMP skip behavior; clip finite unscaled gradients only','controls':summary['controls'],'clipped_updates':summary['clipped_updates'],'amp_skipped_updates':summary['amp_skipped_updates'],'model_promoted':False}
(out/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(out/'evaluation-script.py').write_bytes(Path(__file__).read_bytes())
rows=''.join(f'<tr><td>{c["exam_id"]}</td><td>{c["role"]}</td><td>{c["metrics"]["dice"]:.4f}</td><td>{c["metrics"]["fp"]*c["metrics"]["voxel_ml"]:.3f}</td><td>{c["metrics"]["empty_state"]}</td></tr>' for c in cases)
(out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UCSF clipping intervention</title><style>body{font:17px system-ui;background:#101b2b;color:#ecf3fb;max-width:1100px;margin:30px auto;padding:20px}td,th{padding:10px;border-bottom:1px solid #456;text-align:left}a{color:#80ded0}.scroll{overflow:auto}</style><h1>Gradient clipping: diagnostic intervention</h1><p>The first attempt stopped at update 244 on nonfinite gradients. It is retained as a failed attempt. This separately recorded variant preserves AMP's skipped-update behavior and clips finite unscaled gradients to global L2 norm 1.0.</p><p>Same epoch-four checkpoint, initial probes, all 310 batches and RNG progression as the exact replay. Learning rate, loss, precision and threshold remain unchanged. No active model changed.</p>'''+f'<p>Training subset mean Dice: {groups["train"]["mean_dice"]:.4f}; development validation mean Dice: {groups["development_validation"]["mean_dice"]:.4f}. Control Dice was 0.0000 in both groups. Clipped updates: {summary["clipped_updates"]}; AMP skipped updates: {summary["amp_skipped_updates"]}.</p><div class="scroll"><table><tr><th>Patient</th><th>Role</th><th>Dice</th><th>False-positive mL</th><th>Empty state</th></tr>'+rows+'</table></div><p>This tests a post hoc intervention on one failed trajectory. Nonempty predictions alone are not evidence of adequate segmentation. Full-from-initialization paired-seed testing and independent evaluation remain required.</p><p><a href="evaluation.json">Volume evaluation</a> · <a href="summary.json">Update trace summary</a> · <a href="intervention-protocol.json">Amended protocol</a> · <a href="provenance.json">Provenance</a></p></html>',encoding='utf-8')
print(json.dumps(result,indent=2))
