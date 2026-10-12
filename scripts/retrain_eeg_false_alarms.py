"""Three fixed EEG retraining seeds on the existing eight training recordings."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json
from pathlib import Path
import numpy as np
import torch
from train_eeg_pilot import SeizureCNN
from neurofusion.eeg_alarms import normalize_windows,score_policy,aggregate
from neurofusion.cohort import digest
from neurofusion.data import save_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];old=root/'experiments/eeg-pilot-001';a.output.mkdir(parents=True,exist_ok=False)
    rows=json.loads((old/'prepared-manifest.json').read_text())['records'];baseline=json.loads((root/'experiments/eeg-alarm-reduction-001/summary.json').read_text())
    protocol=dict(seeds=[42,43,44],epochs=10,lr=.001,batch_size=128,positive_weight='sqrt(negative training windows / positive training windows)',
        normalization='Per-window/channel mean removal and RMS division floored at 0.01 original normalized units; clip -8..8; only currently observed four-second window',
        threshold=.5,consecutive_windows=1,selection='Final epoch for every seed; no tuning or seed selection on validation',
        train_patients=['chb01','chb02','chb03','chb04'],validation_patients=['chb05','chb06'],
        acceptance='Every seed reduces false alarm count and background alarm seconds; preserves original matched and timely events for each validation patient',
        validation_reused=True,independent_evaluation=False,recordings=12,downloads=False,
        prepared_manifest_sha256=digest(old/'prepared-manifest.json'))
    save_json(a.output/'protocol.json',protocol);packs={}
    if len(rows)!=12:raise ValueError('Unexpected recording coverage')
    for r in rows:
        if digest(old/r['prepared'])!=r['prepared_sha256'] or digest(root/'data/raw/chbmit-pilot'/r['path'])!=r['sha256']:raise ValueError('EEG source changed')
        pack=np.load(old/r['prepared']);packs[r['path']]=(normalize_windows(pack['x']),pack['y'])
    train=[r for r in rows if r['partition']=='train'];val=[r for r in rows if r['partition']=='validation']
    if set(r['patient'] for r in train)!=set(protocol['train_patients']) or set(r['patient'] for r in val)!=set(protocol['validation_patients']):raise ValueError('Patient roles differ')
    x=torch.from_numpy(np.concatenate([packs[r['path']][0] for r in train]));y=torch.from_numpy(np.concatenate([packs[r['path']][1] for r in train]))
    weight=float(torch.sqrt((len(y)-y.sum())/y.sum()));device='cuda' if torch.cuda.is_available() else 'cpu'
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
    results=[]
    for seed in protocol['seeds']:
        folder=a.output/f'seed{seed}';folder.mkdir();torch.manual_seed(seed);model=SeizureCNN().to(device);optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        criterion=torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight,device=device));history=[]
        for epoch in range(10):
            model.train();losses=[]
            for batch in torch.randperm(len(y)).split(128):
                optimizer.zero_grad();loss=criterion(model(x[batch].to(device)),y[batch].to(device));loss.backward();optimizer.step();losses.append(loss.item())
            history.append(float(np.mean(losses)));print(seed,epoch+1,history[-1],flush=True)
        torch.save(dict(model=model.state_dict(),normalization=protocol['normalization'],protocol_sha256=digest(a.output/'protocol.json'),seed=seed),folder/'last.pt')
        model.eval();case_results=[]
        with torch.inference_mode():
            for r in val:
                prob=np.concatenate([model(b.to(device)).sigmoid().cpu().numpy() for b in torch.from_numpy(packs[r['path']][0]).split(128)])
                path=folder/(Path(r['path']).stem+'.npy');np.save(path,prob)
                case_results.append(dict(path=r['path'],patient=r['patient'],probabilities=path.name,sha256=digest(path),**score_policy(prob,r['events'],r['duration_seconds'])))
        total=aggregate(case_results);patients={k:aggregate([r for r in case_results if r['patient']==k]) for k in protocol['validation_patients']}
        checks=dict(false_alarms_lower=total['false_alarm_events']<baseline['baseline']['false_alarm_events'],
            background_alarm_burden_lower=total['background_alarm_seconds']<baseline['baseline']['background_alarm_seconds'],
            matched_events_preserved=all(patients[k]['matched_events']>=baseline['per_patient']['baseline'][k]['matched_events'] for k in patients),
            timely_events_preserved=all(patients[k]['timely_matched_events']>=baseline['per_patient']['baseline'][k]['timely_matched_events'] for k in patients))
        result=dict(seed=seed,metrics=total,patients=patients,checks=checks,passed=all(checks.values()),
            checkpoint_sha256=digest(folder/'last.pt'),cases=case_results,training_loss=history,positive_weight=weight)
        save_json(folder/'summary.json',result);results.append(result)
    save_json(a.output/'summary.json',dict(results=results,all_seeds_passed=all(r['passed'] for r in results),
        independently_qualified=False,clinical_ready=False,validation_reused=True,baseline=baseline['baseline']))
    print(json.dumps([dict(seed=r['seed'],metrics=r['metrics'],checks=r['checks']) for r in results],indent=2))


if __name__=='__main__':main()
