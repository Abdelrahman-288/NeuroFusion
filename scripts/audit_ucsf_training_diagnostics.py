"""Fixed-subset diagnostic audit of UCSF training failure and false positives."""
import json,hashlib
from pathlib import Path
import torch,numpy as np,nibabel as nib
from neurofusion.tumor_segmentation import TumorUNet
from neurofusion.ucsf_validation import score_native
from neurofusion.ucsf_diagnostics import probability_diagnostics
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-training-diagnostics-001';out.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cache=root/'experiments/ucsf-specialist-cache-001';manifest=read(cache/'manifest.json')
parts=read(root/'experiments/ucsf-specialist-plan-001/partitions.json')
train=sorted([c for c in manifest['cases'] if c['role']=='train'],key=lambda c:hashlib.sha256(('diagnostic-v1:'+c['patient_id']).encode()).hexdigest())[:4]
val=[c for c in manifest['cases'] if c['role']=='development_validation'];selected=train+val
protocol={'purpose':'post hoc training diagnostics, no optimization or promotion','training_subset_selection':'first four SHA256(diagnostic-v1:patient_id); independent of predictions','training_patients':[c['patient_id'] for c in train],'validation_patients':[c['patient_id'] for c in val],'threshold':.5,'probability_histogram_bins':20,'checkpoints':'final for six runs; all five epochs for seed43 baseline','limits':['training subset only, not entire training cohort','all validation patients reused','no threshold sweep','historical gradients not logged; only recorded AMP skipped-update counts available']}
(out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
arrays={};sources={}
for case in selected:
    directory=cache/case['directory']
    for name,checksum in case['sha256'].items():
        if sha(directory/name)!=checksum:raise ValueError('Cache changed')
    record=next(r for r in parts['records'] if r['exam_id']==case['exam_id'])
    source=root/'data/raw/ucsf-pdgm-v5'/record['mask']['path']
    if sha(source)!=record['mask']['sha256']:raise ValueError('Reference changed')
    arrays[case['exam_id']]=(np.load(directory/'images.npy',mmap_mode='r'),np.load(directory/'targets.npy',mmap_mode='r'),read(directory/'geometry.json'),nib.load(source))
    sources[case['exam_id']]={'cache':case['sha256'],'reference_sha256':record['mask']['sha256']}
runs=read(root/'experiments/ucsf-lr-confirmation-001/summary.json')['run_paths'];results=[];checkpoint_hashes={}
model=TumorUNet().cuda()
for seed,paths in runs.items():
    for mode,path in zip(('baseline','candidate'),paths):
        run=root/path;summary=read(run/'summary.json');history=read(run/'history.json')
        for epoch in (range(1,6) if seed=='43' and mode=='baseline' else [5]):
            checkpoint=run/f'epoch-{epoch:02d}.pt';checksum=sha(checkpoint)
            if checksum!=summary['checkpoints'][checkpoint.name]:raise ValueError('Checkpoint changed')
            checkpoint_hashes[str(checkpoint.relative_to(root))]=checksum
            model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=False)['model_state_dict']);model.eval();cases=[]
            with torch.inference_mode():
                for case in selected:
                    x,y,geometry,reference=arrays[case['exam_id']];prob=[]
                    for z in range(0,len(x),8):
                        with torch.autocast('cuda',dtype=torch.float16):logits=model(torch.from_numpy(x[z:z+8].astype(np.float32)/255).cuda())
                        prob.append(logits.float().sigmoid().cpu().numpy()[:,0])
                    probability=np.concatenate(prob)
                    metrics,_=score_native(probability,geometry,reference)
                    if case['role']=='development_validation':
                        recorded=next(c for c in history[epoch-1]['cases'] if c['exam_id']==case['exam_id'])['metrics']
                        if recorded!=metrics:raise ValueError('Historical validation metrics changed')
                    cases.append({'exam_id':case['exam_id'],'role':case['role'],'native_metrics':metrics,'probability':probability_diagnostics(probability,y[:,0])})
            groups={}
            for role in ('train','development_validation'):
                cs=[c for c in cases if c['role']==role]
                groups[role]={'patients':len(cs),'mean_dice':float(np.mean([c['native_metrics']['dice'] for c in cs])),
                  'mean_fp_ml':float(np.mean([c['native_metrics']['fp']*c['native_metrics']['voxel_ml'] for c in cs])),
                  'empty_predictions':sum(c['native_metrics']['empty_state']=='prediction_empty' for c in cs),
                  'max_probability':max(max(c['probability'][g]['max_probability'] or 0 for g in ('foreground','background')) for c in cs)}
            result={'seed':int(seed),'mode':mode,'epoch':epoch,'run':path,'groups':groups,'cases':cases,'training_loss':history[epoch-1]['train_loss'],'amp_skipped_updates':history[epoch-1]['overflow_skipped_updates']}
            results.append(result)
            (out/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
            print(f'{seed} {mode} epoch {epoch}: train-subset Dice {groups["train"]["mean_dice"]:.4f}, validation {groups["development_validation"]["mean_dice"]:.4f}',flush=True)
(out/'provenance.json').write_text(json.dumps({'checkpoints':checkpoint_hashes,'sources':sources,'script_sha256':sha(Path(__file__)),'diagnostics_module_sha256':sha(root/'src/neurofusion/ucsf_diagnostics.py')},indent=2),encoding='utf-8')
(out/'audit-script.py').write_bytes(Path(__file__).read_bytes());(out/'diagnostics-module.py').write_bytes((root/'src/neurofusion/ucsf_diagnostics.py').read_bytes())
print('Diagnostic audit complete; no weights or thresholds changed.',flush=True)
