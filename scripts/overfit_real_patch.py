"""A fixed real TRAINING patch memorization gate, not generalization testing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import nibabel as nib
import numpy as np
import torch
from neurofusion.data import audit, save_json
from neurofusion.preprocessing import prepare_dwi
from neurofusion.segmentation import CompactUNet, segmentation_loss, metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--splits',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=1000)
    args=parser.parse_args()
    if args.output.exists() or not 1<=args.steps<=3000:
        parser.error('Fresh output and 1-3000 steps required')
    manifest=json.loads(args.manifest.read_text())
    splits=json.loads(args.splits.read_text())
    if not splits.get('frozen') or splits.get('manifest_sha256')!=hashlib.sha256(args.manifest.read_bytes()).hexdigest() or not audit(manifest,splits)['passed']:
        parser.error('Frozen audited manifest/splits required')
    if not torch.cuda.is_available():
        parser.error('CUDA required')
    study=next(s for s in manifest['studies'] if splits['assignments'][s['subject_id']]=='train' and s['files']['mask']['lesion_voxels']>0)
    root=Path(manifest['data_root']).resolve()
    paths=[(root/study['files'][m]['path']).resolve() for m in ['dwi','mask']]
    if not all(p.is_relative_to(root) for p in paths):
        raise ValueError('Path outside root')
    meta=prepare_dwi(*paths,args.output/'prepared')
    if any(meta[m+'_sha256']!=study['files'][m]['sha256'] for m in ['dwi','mask']):
        raise ValueError('Source changed')
    image=nib.load(args.output/'prepared/dwi.nii.gz').get_fdata(dtype=np.float32)
    label=nib.load(args.output/'prepared/mask.nii.gz').get_fdata(dtype=np.float32)
    center=np.argwhere(label>0)[len(np.argwhere(label>0))//2]
    size=32
    image=np.pad(image,[(0,max(0,size-s)) for s in image.shape])
    label=np.pad(label,[(0,max(0,size-s)) for s in label.shape])
    start=np.maximum(0,np.minimum(center-size//2,np.array(image.shape)-size))
    region=tuple(slice(int(s),int(s)+size) for s in start)
    patch,target=image[region].copy(),label[region].copy()
    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    model=CompactUNet().cuda()
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    tx=torch.from_numpy(patch)[None,None].cuda()
    ty=torch.from_numpy(target)[None,None].cuda()
    history=[]
    started=time.perf_counter()
    for step in range(args.steps):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss=segmentation_loss(model(tx),ty)
        if not torch.isfinite(loss):
            raise RuntimeError('Nonfinite loss')
        loss.backward()
        optimizer.step()
        history.append({'step':step+1,'loss':float(loss.detach().cpu())})
        if (step+1)%100==0:
            print(json.dumps(history[-1]),flush=True)
    model.eval()
    with torch.no_grad():
        probability=model(tx).sigmoid()[0,0].cpu().numpy()
    score=metrics(probability,target)
    report={'purpose':'Fixed real TRAINING patch memorization, not validation performance',
            'subject':study['subject_id'],'partition':'train','patch_start':start.tolist(),'patch_size':size,
            'steps':args.steps,'metrics':score,'elapsed_seconds':time.perf_counter()-started,
            'initial_loss':history[0]['loss'],'final_loss':history[-1]['loss'],
            'pass_criterion':'Training-patch Dice >= 0.95 and final loss below initial loss',
            'passed':score['dice']>=.95 and history[-1]['loss']<history[0]['loss'],
            'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest()}
    save_json(args.output/'report.json',report)
    save_json(args.output/'history.json',history)
    np.savez_compressed(args.output/'patch-results.npz',image=patch,reference=target,probability=probability)
    torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'report':report},args.output/'overfit-checkpoint.pt')
    # Separate wording to avoid confusing memorization with validation.
    points=' '.join(f'{30+i*730/max(1,len(history)-1):.1f},{240-r["loss"]/max(h["loss"] for h in history)*200:.1f}' for i,r in enumerate(history))
    (args.output/'progress.html').write_text(f'<!doctype html><meta charset="utf-8"><title>Real training-patch check</title><style>body{{font:18px system-ui;margin:40px auto;max-width:950px;padding:20px}}svg{{width:100%;background:#f1f6f9}}</style><h1>Real training-patch overfit check</h1><p>Training Dice: {score["dice"]:.4f}. Same patch used for fitting and scoring; not validation accuracy.</p><svg viewBox="0 0 800 270"><polyline points="{points}" fill="none" stroke="teal" stroke-width="2"/></svg><p><a href="report.json">Run report</a></p>',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
