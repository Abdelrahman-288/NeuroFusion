"""Reload every EEG candidate and independently replay validation decisions."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json
from pathlib import Path
import numpy as np
import torch
from train_eeg_pilot import SeizureCNN
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.eeg_alarms import normalize_windows,score_policy,aggregate

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];old=root/'experiments/eeg-pilot-001';read=lambda p:json.loads(p.read_text())
report=read(a.run/'summary.json');protocol=read(a.run/'protocol.json');manifest=read(old/'prepared-manifest.json')
if digest(old/'prepared-manifest.json')!=protocol['prepared_manifest_sha256']:raise ValueError('Prepared manifest changed')
torch.set_num_threads(2);device='cuda' if torch.cuda.is_available() else 'cpu';proof=[]
for result in report['results']:
    folder=a.run/f"seed{result['seed']}";path=folder/'last.pt'
    if digest(path)!=result['checkpoint_sha256']:raise ValueError('Checkpoint changed')
    checkpoint=torch.load(path,map_location=device,weights_only=True)
    if checkpoint['protocol_sha256']!=digest(a.run/'protocol.json'):raise ValueError('Protocol changed')
    model=SeizureCNN().to(device);model.load_state_dict(checkpoint['model']);model.eval();rows=[]
    with torch.inference_mode():
        for row in result['cases']:
            source=next(r for r in manifest['records'] if r['path']==row['path'])
            if source['partition']!='validation' or digest(old/source['prepared'])!=source['prepared_sha256']:raise ValueError('Validation features changed')
            values=normalize_windows(np.load(old/source['prepared'])['x'])
            p=np.concatenate([model(b.to(device)).sigmoid().cpu().numpy() for b in torch.from_numpy(values).split(128)])
            if digest(folder/row['probabilities'])!=row['sha256']:raise ValueError('Saved probabilities changed')
            saved=np.load(folder/row['probabilities']);delta=float(np.max(np.abs(p-saved)))
            if delta>1e-6 or not np.array_equal(p>=.5,saved>=.5):raise ValueError('Checkpoint does not reproduce')
            metrics=score_policy(p,source['events'],source['duration_seconds'])
            if any(row[k]!=v for k,v in metrics.items()):raise ValueError('Event metrics differ')
            rows.append(metrics);proof.append(dict(seed=result['seed'],recording=row['path'],max_difference=delta))
    if aggregate(rows)!=result['metrics']:raise ValueError('Aggregate differs')
save_json(a.run/'verification.json',dict(passed=True,checkpoints=3,prediction_arrays=len(proof),records=proof,
    summary_sha256=digest(a.run/'summary.json'),independent_validation=False))
print('Verified all three checkpoints and twelve validation prediction arrays')
