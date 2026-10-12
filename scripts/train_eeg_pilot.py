"""Real-data EEG engineering pilot; no diagnostic or population-performance claim."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import json
from pathlib import Path
import numpy as np
import pyedflib
from scipy.signal import butter,sosfilt,resample_poly
import torch
from torch import nn
from neurofusion.eeg import CHANNELS,event_scores
from neurofusion.cohort import digest
from neurofusion.data import save_json

class SeizureCNN(nn.Module):
    def __init__(self):
        super().__init__();self.network=nn.Sequential(nn.Conv1d(6,16,9,stride=4,padding=4),nn.GroupNorm(4,16),nn.ReLU(),
            nn.Conv1d(16,32,9,stride=4,padding=4),nn.GroupNorm(4,32),nn.ReLU(),nn.Conv1d(32,32,5,padding=2),nn.ReLU(),nn.AdaptiveAvgPool1d(1),nn.Flatten(),nn.Linear(32,1))
    def forward(self,x):return self.network(x).squeeze(1)

def main():
    root=Path(__file__).resolve().parents[1];out=root/'experiments/eeg-pilot-001';data=root/'data/raw/chbmit-pilot'
    protocol=json.loads((out/'protocol.json').read_text());manifest=json.loads((out/'download-manifest.json').read_text())
    if (out/'last.pt').exists() or (out/'prepared').exists():raise ValueError('Training artifacts already exist')
    assert manifest['records']==protocol['records']
    records=[];filter_sos=butter(4,[.5,40],btype='bandpass',fs=256,output='sos')
    for row in manifest['records']:
        path=data/row['path']
        if digest(path)!=row['sha256']:raise ValueError('EDF source changed')
        with pyedflib.EdfReader(str(path)) as reader:
            labels=[s.strip() for s in reader.getSignalLabels()]
            arrays=[]
            for name in CHANNELS:
                indices=[i for i,s in enumerate(labels) if s==name]
                if len(indices)!=1:raise ValueError('Required unique bipolar channel missing: '+name)
                i=indices[0]
                if reader.getSampleFrequency(i)!=256:raise ValueError('Expected 256 Hz')
                unit=reader.getPhysicalDimension(i).strip().lower()
                if unit not in ('uv','µv','μv'):raise ValueError('Expected microvolt physical samples')
                values=reader.readSignal(i)
                if not np.isfinite(values).all():raise ValueError('Nonfinite EEG')
                # Causal anti-alias filter, then causal decimation; no future samples.
                filtered=sosfilt(filter_sos,values)[::2]
                arrays.append(np.clip(filtered/100.,-20,20).astype(np.float32))
        if len({len(a) for a in arrays})!=1:raise ValueError('Unequal channel lengths')
        x=np.stack(arrays);n=x.shape[1]//512;duration=n*4.
        if any(b>duration for a,b in row['events']):raise ValueError('Annotated event extends beyond evaluated full windows')
        windows=x[:,:n*512].reshape(6,n,512).transpose(1,0,2).copy()
        target=np.array([any(max(i*4,a)<min((i+1)*4,b) for a,b in row['events']) for i in range(n)],dtype=np.float32)
        folder=out/'prepared';folder.mkdir(exist_ok=True)
        file=folder/(Path(row['path']).stem+'.npz');np.savez_compressed(file,x=windows,y=target)
        records.append({**row,'windows':n,'duration_seconds':duration,'positive_windows':int(target.sum()),'prepared_sha256':digest(file),'prepared':str(file.relative_to(out))})
        print('Prepared '+row['path'],flush=True)
    save_json(out/'prepared-manifest.json',{'records':records,'protocol_sha256':digest(out/'protocol.json')})
    train=[r for r in records if r['partition']=='train'];validation=[r for r in records if r['partition']=='validation']
    if {r['patient'] for r in train}&{r['patient'] for r in validation}:raise ValueError('Patient leakage')
    packs=[np.load(out/r['prepared'],allow_pickle=False) for r in train]
    x=torch.from_numpy(np.concatenate([r['x'] for r in packs]));y=torch.from_numpy(np.concatenate([r['y'] for r in packs]))
    torch.manual_seed(42);torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    device='cuda' if torch.cuda.is_available() else 'cpu';model=SeizureCNN().to(device)
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    weight=(len(y)-y.sum())/y.sum()
    criterion=nn.BCEWithLogitsLoss(pos_weight=weight.to(device))
    history=[]
    for epoch in range(1,11):
        model.train();losses=[]
        for batch in torch.randperm(len(y)).split(128):
            optimizer.zero_grad();loss=criterion(model(x[batch].to(device)),y[batch].to(device));loss.backward();optimizer.step();losses.append(loss.item())
        history.append({'epoch':epoch,'mean_training_loss':float(np.mean(losses))});print(history[-1],flush=True)
    torch.save({'model':model.state_dict(),'architecture':'six-channel-cnn-v1','channels':list(CHANNELS),'epoch':10,'protocol_sha256':digest(out/'protocol.json')},out/'last.pt')
    model=SeizureCNN().to(device);model.load_state_dict(torch.load(out/'last.pt',weights_only=True,map_location=device)['model']);model.eval()
    results=[]
    with torch.inference_mode():
        for row in validation:
            pack=np.load(out/row['prepared'],allow_pickle=False)
            p=np.concatenate([model(batch.to(device)).sigmoid().cpu().numpy() for batch in torch.from_numpy(pack['x']).split(128)])
            scores=event_scores(p,row['events'],row['duration_seconds'])
            filename=Path(row['path']).stem+'-probabilities.npy';np.save(out/filename,p,allow_pickle=False)
            truth=pack['y']>0;pred=p>=.5
            results.append({**row,**scores,'tp_windows':int((truth&pred).sum()),'fp_windows':int((~truth&pred).sum()),
                'fn_windows':int((truth&~pred).sum()),'tn_windows':int((~truth&~pred).sum()),'probabilities':filename,'probability_sha256':digest(out/filename)})
    ref=sum(r['reference_events'] for r in results);matched=sum(r['matched_events'] for r in results)
    false=sum(r['false_alarm_events'] for r in results);hours=sum(r['background_hours'] for r in results)
    report={'training_patients':len({r['patient'] for r in train}),'validation_patients':len({r['patient'] for r in validation}),
        'source_recordings':len(records),'training_windows':len(y),'validation_recordings':len(results),'validation_duration_hours':sum(r['duration_seconds'] for r in results)/3600,
        'reference_events':ref,'matched_events':matched,'event_sensitivity':matched/ref if ref else None,'false_alarm_events':false,'false_alarms_per_background_hour':false/hours,
        'records':results,'history':history,'checkpoint_sha256':digest(out/'last.pt'),'protocol_sha256':digest(out/'protocol.json'),'runner_sha256':digest(Path(__file__)),
        'independently_qualified':False,'clinical_ready':False,'promotion_permitted':False,
        'limitations':'Label-selected 12-recording six-patient pilot, two validation patients; not representative continuous screening or independent clinical validation. Causal filtering/decimation and window-end decisions introduce latency. No tuning on validation.'}
    save_json(out/'summary.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('records','history')},indent=2))

if __name__=='__main__':main()
