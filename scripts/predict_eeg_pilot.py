"""Apply the verified research alarm policy to an existing prepared pilot recording."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from train_eeg_pilot import SeizureCNN
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.eeg_alarms import apply_alarm_policy

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recording',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];old=root/'experiments/eeg-pilot-001';policy_path=root/'experiments/eeg-conservative-001/policy.json'
policy=json.loads(policy_path.read_text());rows=json.loads((old/'prepared-manifest.json').read_text())['records']
matches=[r for r in rows if r['path']==a.recording]
if len(matches)!=1:raise ValueError('Select one existing pilot recording by its manifest path')
row=matches[0];sha=digest(old/'last.pt')
if digest(old/row['prepared'])!=row['prepared_sha256'] or digest(root/'data/raw/chbmit-pilot'/row['path'])!=row['sha256']:raise ValueError('Source or prepared recording changed')
torch.set_num_threads(2);device='cuda' if torch.cuda.is_available() else 'cpu';model=SeizureCNN().to(device)
model.load_state_dict(torch.load(old/'last.pt',weights_only=True,map_location=device)['model']);model.eval()
x=np.load(old/row['prepared'])['x']
with torch.inference_mode():prob=np.concatenate([model(b.to(device)).sigmoid().cpu().numpy() for b in torch.from_numpy(x).split(128)])
active=apply_alarm_policy(prob,policy,sha)
a.output.mkdir(parents=True,exist_ok=False);np.savez_compressed(a.output/'windows.npz',probabilities=prob,confirmed=active,decision_times_seconds=(np.arange(len(prob))+1)*4)
save_json(a.output/'result.json',dict(recording=a.recording,source_sha256=row['sha256'],checkpoint_sha256=sha,policy_sha256=digest(policy_path),
    policy=policy,windows=len(prob),confirmed_windows=int(active.sum()),labels_used=False,
    research_only=True,clinical_ready=False,warning='False alarms remain excessive; positive windows are not confirmed seizures'))
print(a.output/'result.json')
