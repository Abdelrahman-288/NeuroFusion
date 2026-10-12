"""Reproduce pilot probabilities from the saved final EEG checkpoint."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import json
from pathlib import Path
import numpy as np
import torch
from train_eeg_pilot import SeizureCNN
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.eeg import event_scores
root=Path(__file__).resolve().parents[1];out=root/'experiments/eeg-pilot-001'
read=lambda p:json.loads(p.read_text())
r=read(out/'summary.json');protocol=read(out/'protocol.json')
assert r['checkpoint_sha256']==digest(out/'last.pt') and r['protocol_sha256']==digest(out/'protocol.json')
torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
device='cuda' if torch.cuda.is_available() else 'cpu';model=SeizureCNN().to(device)
checkpoint=torch.load(out/'last.pt',map_location=device,weights_only=True)
assert checkpoint['epoch']==protocol['training']['epochs']
model.load_state_dict(checkpoint['model']);model.eval();cases=[]
with torch.inference_mode():
    for row in r['records']:
        assert digest(root/'data/raw/chbmit-pilot'/row['path'])==row['sha256']
        assert digest(out/row['prepared'])==row['prepared_sha256']
        assert digest(out/row['probabilities'])==row['probability_sha256']
        pack=np.load(out/row['prepared'],allow_pickle=False)
        p=np.concatenate([model(batch.to(device)).sigmoid().cpu().numpy() for batch in torch.from_numpy(pack['x']).split(128)])
        saved=np.load(out/row['probabilities'],allow_pickle=False)
        difference=float(np.max(np.abs(p-saved)))
        assert difference<=1e-6 and np.array_equal(p>=.5,saved>=.5)
        metrics=event_scores(p,row['events'],row['duration_seconds'])
        for k in ['matched_events','false_alarm_events','reference_events']:assert metrics[k]==row[k]
        cases.append({'path':row['path'],'max_probability_difference':difference})
save_json(out/'verification.json',{'passed':True,'cases':cases,'summary_sha256':digest(out/'summary.json'),
    'checkpoint_sha256':digest(out/'last.pt'),'scope':'Saved-feature checkpoint replay and event accounting; not independent clinical verification'})
print('EEG final checkpoint and event metrics reproduced')
