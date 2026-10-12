"""Bounded real-data DWI pipeline run; not a full-cohort benchmark."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import time

import nibabel as nib
import numpy as np
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import torch

from neurofusion.data import audit, save_json
from neurofusion.preprocessing import prepare_dwi, restore_prediction
from neurofusion.segmentation import CompactUNet, metrics, predict_volume, sample_patch, segmentation_loss


def render_progress(output, history, validations, status):
    losses=[r['loss'] for r in history]
    top=max(losses,default=1)
    points=' '.join(f'{30+i*730/max(1,len(losses)-1):.1f},{240-v/top*200:.1f}' for i,v in enumerate(losses))
    rows=''.join(f"<tr><td>{v['step']}</td><td>{v['mean_dice']:.4f}</td><td>{len(v['cases'])}</td></tr>" for v in validations)
    content=f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>NeuroFusion real-data run</title>
<style>body{{font:17px system-ui;max-width:950px;margin:40px auto;padding:20px;color:#173348}}svg{{background:#f1f6f9;width:100%}}td,th{{padding:10px;text-align:left}}.note{{background:#fff3ce;padding:15px}}</style></head><body>
<h1>NeuroFusion: small real-data baseline</h1><p>{html.escape(status)} · Training steps completed: {len(history)}</p>
<p class="note">Four training studies and two validation studies by default. Preliminary pipeline check, not a full-cohort result or clinical accuracy estimate. Holdout is not evaluated.</p>
<h2>Patch training loss</h2><svg viewBox="0 0 800 275" role="img" aria-label="Training loss curve"><polyline points="{points}" fill="none" stroke="#008080" stroke-width="2"/></svg>
<h2>Full-volume validation</h2><table><tr><th>Step</th><th>Mean Dice</th><th>Studies</th></tr>{rows}</table>
<p>Metrics use a fixed 0.5 probability threshold. <a href="history.json">Training history</a> · <a href="validation.json">Per-case results</a> · <a href="config.json">Run configuration</a></p></body></html>'''
    temporary=output/'progress.tmp'
    temporary.write_text(content,encoding='utf-8')
    temporary.replace(output/'progress.html')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--splits',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=200)
    parser.add_argument('--train-cases',type=int,default=4)
    parser.add_argument('--val-cases',type=int,default=2)
    parser.add_argument('--resume',type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.steps<1 or not 1<=args.train_cases<=16 or not 1<=args.val_cases<=4:
        parser.error('Use a new output directory, positive steps, 1-16 train cases and 1-4 validation cases')
    if not torch.cuda.is_available():
        parser.error('CUDA required')
    manifest=json.loads(args.manifest.read_text())
    splits=json.loads(args.splits.read_text())
    manifest_hash=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    if not splits.get('frozen') or splits.get('manifest_sha256')!=manifest_hash or not audit(manifest,splits)['passed']:
        parser.error('Require a frozen split bound to this manifest and a passing leakage audit')
    def select(partition,count):
        choices=sorted([s for s in manifest['studies'] if splits['assignments'][s['subject_id']]==partition],key=lambda s:s['subject_id'])
        if len(choices)<count:
            raise ValueError('Not enough studies in partition')
        # Fixed identity-based ordering, never model-performance-based selection.
        return choices[:count]
    training=select('train',args.train_cases)
    validation=select('validation',args.val_cases)
    config={'architecture':'compact-unet-8-16-32-groupnorm','seed':42,'patch':32,'lr':.001,
            'upsampling':'nearest','downsampling':'stride2-convolution','deterministic_algorithms':True,'torch':str(torch.__version__),
            'loss':'BCE + soft Dice','sampling':'50% lesion-center if present, otherwise uniform spatial center',
            'manifest_sha256':manifest_hash,'splits_sha256':hashlib.sha256(args.splits.read_bytes()).hexdigest(),
            'train_subjects':[s['subject_id'] for s in training],'validation_subjects':[s['subject_id'] for s in validation],
            'threshold':.5,'sliding_window_overlap':.5,'input':'DWI only, native spacing, canonical RAS, nonzero zscore',
            'limitations':'Small pipeline run; not cohort benchmark. Variable native voxel spacing. Holdout unused.'}
    checkpoint=torch.load(args.resume,weights_only=True,map_location='cpu') if args.resume else None
    if checkpoint and (checkpoint['config']!=config or checkpoint['step']>=args.steps):
        parser.error('Resume requires identical config/data and a larger total step target')
    args.output.mkdir(parents=True)
    save_json(args.output/'config.json',config)
    root=Path(manifest['data_root']).resolve()
    loaded={}
    for study in training+validation:
        folder=args.output/'prepared'/study['subject_id']
        paths=[(root/study['files'][k]['path']).resolve() for k in ('dwi','mask')]
        if not all(p.is_relative_to(root) for p in paths):
            raise ValueError('Source path escapes dataset root')
        meta=prepare_dwi(paths[0],paths[1],folder)
        if any(meta[k+'_sha256']!=study['files'][k]['sha256'] for k in ('dwi','mask')):
            raise ValueError('Source changed since manifest')
        loaded[study['subject_id']]=(nib.load(folder/'dwi.nii.gz').get_fdata(dtype=np.float32),
                                    nib.load(folder/'mask.nii.gz').get_fdata(dtype=np.float32),meta)
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    torch.set_num_threads(2)
    rng=np.random.default_rng(42)
    model=CompactUNet().cuda()
    optimizer=torch.optim.Adam(model.parameters(),lr=config['lr'])
    scaler=torch.amp.GradScaler('cuda')
    history,validations=[],[]
    start_step=0
    best=-1.
    if checkpoint:
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        scaler.load_state_dict(checkpoint['scaler'])
        rng.bit_generator.state=checkpoint['numpy_rng']
        torch.set_rng_state(checkpoint['torch_rng'])
        torch.cuda.set_rng_state_all(checkpoint['cuda_rng'])
        history,validations=checkpoint['history'],checkpoint['validations']
        start_step,best=checkpoint['step'],checkpoint['best_dice']
    torch.cuda.reset_peak_memory_stats()
    clock=time.perf_counter()
    def save_checkpoint(step,name):
        temp=args.output/(name+'.tmp')
        torch.save({'step':step,'config':config,'model':model.state_dict(),'optimizer':optimizer.state_dict(),
                    'scaler':scaler.state_dict(),'numpy_rng':rng.bit_generator.state,'torch_rng':torch.get_rng_state(),
                    'cuda_rng':torch.cuda.get_rng_state_all(),'history':history,'validations':validations,'best_dice':best},temp)
        temp.replace(args.output/name)
    render_progress(args.output,history,validations,'Running')
    for step in range(start_step,args.steps):
        model.train()
        identity=training[int(rng.integers(len(training)))]['subject_id']
        x,y,_=loaded[identity]
        patch,label=sample_patch(x,y,rng,size=config['patch'])
        tx=torch.from_numpy(patch)[None,None].cuda()
        ty=torch.from_numpy(label)[None,None].cuda()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type='cuda',dtype=torch.float16):
            loss=segmentation_loss(model(tx),ty)
        if not torch.isfinite(loss):
            raise RuntimeError('Nonfinite training loss')
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        history.append({'step':step+1,'loss':float(loss.detach().cpu()),'subject':identity})
        if (step+1)%25==0:
            save_json(args.output/'history.json',history)
            render_progress(args.output,history,validations,'Running')
            print(json.dumps(history[-1]),flush=True)
        if (step+1)%100==0 or step+1==args.steps:
            cases=[]
            for study in validation:
                subject=study['subject_id']
                x,y,meta=loaded[subject]
                probability=predict_volume(model,x,'cuda',patch=config['patch'])
                cases.append({'subject':subject,**metrics(probability,y)})
                if step+1==args.steps:
                    restore_prediction(probability,meta,args.output/'predictions'/f'{subject}-probability.nii.gz')
            score=float(np.mean([c['dice'] for c in cases]))
            validations.append({'step':step+1,'mean_dice':score,'cases':cases})
            if score>best:
                best=score
                save_checkpoint(step+1,'best.pt')
            save_checkpoint(step+1,'last.pt')
            save_json(args.output/'validation.json',validations)
            print(json.dumps({'step':step+1,'validation_mean_dice':score}),flush=True)
    torch.cuda.synchronize()
    save_json(args.output/'history.json',history)
    summary={'completed':True,'total_steps':args.steps,'resumed_from_step':start_step,
             'elapsed_seconds_this_run':time.perf_counter()-clock,'peak_vram_bytes':torch.cuda.max_memory_allocated(),
             'parameters':sum(p.numel() for p in model.parameters()),'last_validation':validations[-1],
             'best_validation_dice_in_lineage':best,'holdout_evaluated':False,'torch':str(torch.__version__),
             'gpu':torch.cuda.get_device_name(),'limitations':config['limitations']}
    save_json(args.output/'summary.json',summary)
    render_progress(args.output,history,validations,'Completed')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
