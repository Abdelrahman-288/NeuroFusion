"""Bounded GPU overfit check on one explicitly synthetic study, not evaluation."""
import argparse
import csv
import json
from pathlib import Path
import time

import nibabel as nib
import numpy as np
import torch
from torch import nn

from neurofusion.data import save_json
from neurofusion.demo import create_demo
from neurofusion.preprocessing import prepare_dwi, restore_prediction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=200)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.steps <= 1000:
        parser.error('Use a new output directory and 1-1000 steps')
    if not torch.cuda.is_available():
        parser.error('CUDA is required for this GPU check')
    torch.manual_seed(42)
    np.random.seed(42)
    create_demo(args.output/'synthetic', patients=1)
    source = args.output/'synthetic/synthetic-000'
    prepared = args.output/'prepared'
    metadata = prepare_dwi(source/'dwi.nii.gz', source/'mask.nii.gz', prepared)
    x = torch.from_numpy(nib.load(prepared/'dwi.nii.gz').get_fdata(dtype=np.float32).copy())[None,None].cuda()
    y = torch.from_numpy(nib.load(prepared/'mask.nii.gz').get_fdata(dtype=np.float32).copy())[None,None].cuda()
    model = nn.Sequential(nn.Conv3d(1,8,3,padding=1),nn.ReLU(),nn.Conv3d(8,8,3,padding=1),
                          nn.ReLU(),nn.Conv3d(8,1,1)).cuda()
    optimizer = torch.optim.Adam(model.parameters(),lr=.01)
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([5.],device='cuda'))
    history = []
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    for step in range(args.steps):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(x), y)
        if not torch.isfinite(loss):
            raise RuntimeError('Nonfinite loss')
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            prediction = model(x).sigmoid() >= .5
            dice = (2*(prediction*y).sum() / (prediction.sum()+y.sum()).clamp(min=1)).item()
        history.append({'step':step+1,'loss':loss.item(),'training_dice':dice})
        if (step+1) % 25 == 0:
            print(json.dumps(history[-1]),flush=True)
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-start
    checkpoint = args.output/'debug-checkpoint.pt'
    torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':args.steps,
                'seed':42,'architecture':'Conv3d 1-8-8-1, ReLU, native grid',
                'purpose':'synthetic single-study overfit debug only'}, checkpoint)
    reloaded = torch.load(checkpoint,weights_only=True)
    model.load_state_dict(reloaded['model'])
    optimizer.load_state_dict(reloaded['optimizer'])
    with torch.no_grad():
        probabilities = model(x).sigmoid()[0,0].cpu().numpy()
    restore_prediction(probabilities,metadata,args.output/'probability-native.nii.gz')
    with (args.output/'history.csv').open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    report = {'purpose':'Synthetic single-study overfit check; no generalization or clinical evidence',
              'device':torch.cuda.get_device_name(),'steps':args.steps,'elapsed_seconds':elapsed,
              'peak_vram_bytes':torch.cuda.max_memory_allocated(),'initial_loss':history[0]['loss'],
              'final_loss':history[-1]['loss'],'training_dice':history[-1]['training_dice'],
              'passed':history[-1]['training_dice'] >= .95 and history[-1]['loss'] < history[0]['loss'],
              'checkpoint_reload_verified':True,'preprocessing':metadata}
    save_json(args.output/'report.json', report)
    # Self-contained, local HTML chart. No hosted data or external JavaScript.
    values = [h['loss'] for h in history]
    high = max(values)
    points = ' '.join(f'{40+i*720/max(1,len(values)-1):.1f},{250-v/high*210:.1f}' for i,v in enumerate(values))
    (args.output/'progress.html').write_text(f'''<!doctype html><html><meta charset="utf-8">
<title>NeuroFusion synthetic training check</title><style>body{{font:17px system-ui;max-width:900px;margin:40px auto;padding:20px;color:#15334b}}svg{{width:100%;background:#f3f7fa}}code{{background:#eee}}</style>
<h1>NeuroFusion: synthetic training check</h1><p>One artificial study, evaluated on the same training voxels. This is a debugging result, not medical accuracy.</p>
<p>Steps: {args.steps} · Training Dice: {report['training_dice']:.3f} · Time: {elapsed:.1f}s</p>
<h2>Training loss</h2><svg viewBox="0 0 800 290" role="img" aria-label="Training loss curve"><polyline fill="none" stroke="#008080" stroke-width="3" points="{points}"/><text x="40" y="278">Step 1</text><text x="700" y="278">Step {args.steps}</text></svg>
<p>Initial loss {values[0]:.4f}; final loss {values[-1]:.4f}. Exact values: <a href="history.csv">history.csv</a>. <a href="report.json">Run report</a>.</p></html>''',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'preprocessing'},indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
