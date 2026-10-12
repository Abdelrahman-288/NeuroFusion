"""Two simulated clients, local/centralized/FedAvg comparison and round recovery."""
import argparse
import copy
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch.nn import functional as F
from neurofusion.external_import import digest
from neurofusion.federated import aggregate
from neurofusion.tumor_segmentation import TumorUNet,segmentation_loss

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def cpu_state(model):return {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False)
    cache=ROOT/'experiments/ucsf-specialist-cache-001';partition=ROOT/'experiments/ucsf-specialist-plan-001/partitions.json'
    parts=read(partition);manifest=read(cache/'manifest.json')
    if manifest['partitions_sha256']!=digest(partition):raise ValueError('Partition changed')
    protected={r['patient_id'] for r in read(ROOT/'experiments/ucsf-acquisition-001/summary.json')['results']}
    if protected&{r['patient_id'] for r in parts['records']}:raise ValueError('Protected patient overlap')
    # Ascending case ID split deliberately has nonidentical patient distributions, not real hospitals.
    train=sorted(parts['train_patients']);validation=sorted(parts['development_validation_patients'])
    clients={'client-a':train[:8],'client-b':train[8:]};val_clients={'client-a':validation[:2],'client-b':validation[2:]}
    plan={'seed':42,'rounds':2,'local_epochs_per_round':1,'central_epochs':2,'local_only_epochs':2,'batch_size':16,'size':120,'threshold':.5,'optimizer':'Adam reset at every round/epoch for all arms','learning_rate':.001,'gradient_clip':1.,'aggregation':'sample-weighted synchronous FedAvg','client_training_patients':clients,'client_validation_patients':val_clients,'client_definition':'simulated ascending-ID partitions, not institutions','checkpoint_rule':'fixed final round','metric':'120x120-grid per-patient numeric-foreground Dice','clinical_ready':False,'differential_privacy':False,'secure_aggregation':False,'network_training':False}
    save(out/'protocol.json',plan);save(out/'provenance.json',{'partitions':digest(partition),'cache':digest(cache/'manifest.json'),'runner':digest(Path(__file__)),'aggregation':digest(ROOT/'src/neurofusion/federated.py')})
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    x={};y={};source_rows={r['exam_id']:r for r in parts['records']}
    for row in manifest['cases']:
        exam=row['exam_id'];directory=cache/row['directory'];source=source_rows[exam]
        if row['role']!=source['role'] or row['patient_id']!=source['patient_id']:raise ValueError('Partition mismatch')
        for name,checksum in row['sha256'].items():
            if digest(directory/name)!=checksum:raise ValueError('Cache changed')
        for key in ('image','mask'):
            if digest(ROOT/'data/raw/ucsf-pdgm-v5'/source[key]['path'])!=source[key]['sha256']:raise ValueError('Source changed')
        x[exam]=F.interpolate(torch.from_numpy(np.load(directory/'images.npy').astype(np.float32)/255),size=(120,120),mode='bilinear',align_corners=False)
        y[exam]=F.interpolate(torch.from_numpy(np.load(directory/'targets.npy').astype(np.float32)),size=(120,120),mode='nearest')
    def fit(state,exams,seed):
        torch.manual_seed(seed);model=TumorUNet().cuda();model.load_state_dict(state);optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        xx=torch.cat([x[e] for e in exams]);yy=torch.cat([y[e] for e in exams]);losses=[]
        for batch in torch.randperm(len(xx),generator=torch.Generator().manual_seed(seed)).split(16):
            optimizer.zero_grad(set_to_none=True);loss=segmentation_loss(model(xx[batch].cuda()),yy[batch].cuda())
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();losses.append(loss.item())
        return cpu_state(model),float(np.mean(losses)),len(xx)
    def evaluate(state):
        model=TumorUNet().cuda();model.load_state_dict(state);model.eval();scores=[]
        with torch.inference_mode():
            for exam in validation:
                pred=torch.cat([model(b.cuda()).sigmoid().cpu()>=.5 for b in x[exam].split(16)]);truth=y[exam]>0;den=int(pred.sum()+truth.sum())
                scores.append({'exam':exam,'dice':2*int((pred&truth).sum())/den if den else 1.})
        return {'cases':scores,'mean_dice':float(np.mean([r['dice'] for r in scores])),'by_simulated_client':{c:float(np.mean([r['dice'] for r in scores if r['exam'] in ids])) for c,ids in val_clients.items()}}
    started=time.time();torch.manual_seed(42);initial=cpu_state(TumorUNet());results={}
    for arm,exams in [('centralized',train),*clients.items()]:
        state=copy.deepcopy(initial);draws=0;losses=[]
        for epoch in range(2):state,loss,n=fit(state,exams,42+epoch);draws+=n;losses.append(loss)
        torch.save(state,out/(arm+'.pt'));results[arm]={'evaluation':evaluate(state),'training_slice_draws':draws,'losses':losses,'checkpoint_sha256':digest(out/(arm+'.pt'))};print(arm,results[arm]['evaluation']['mean_dice'],flush=True)
    state=copy.deepcopy(initial);draws=0;rounds=[]
    for round_id in (1,2):
        updates=[]
        for index,(client,exams) in enumerate(clients.items()):
            update,loss,n=fit(state,exams,420+10*round_id+index);updates.append({'client':client,'state':update,'samples':n});draws+=n
        state=aggregate(updates,list(clients));torch.save({'state':state,'round':round_id,'protocol_sha256':digest(out/'protocol.json')},out/f'round-{round_id}.pt');rounds.append({'round':round_id,'sha256':digest(out/f'round-{round_id}.pt')})
    torch.save(state,out/'federated.pt');results['federated']={'evaluation':evaluate(state),'training_slice_draws':draws,'rounds':rounds,'checkpoint_sha256':digest(out/'federated.pt')}
    # Resume exactly the second round from the saved first-round checkpoint.
    recovered=torch.load(out/'round-1.pt',weights_only=True,map_location='cpu')
    if recovered['protocol_sha256']!=digest(out/'protocol.json') or recovered['round']!=1:raise ValueError('Recovery protocol mismatch')
    replay=[]
    for index,(client,exams) in enumerate(clients.items()):
        update,_,n=fit(recovered['state'],exams,440+index);replay.append({'client':client,'state':update,'samples':n})
    replay=aggregate(replay,list(clients));recovery=all(torch.equal(state[k],replay[k]) for k in state)
    if not recovery:raise ValueError('Round recovery differs')
    for arm,result in results.items():
        restored=torch.load(out/(arm+'.pt'),weights_only=True,map_location='cpu')
        if evaluate(restored)!=result['evaluation']:raise ValueError('Checkpoint metric reproduction differs')
    summary={'arms':results,'round_recovery_exact':recovery,'saved_metrics_reproduced':True,'central_and_federated_slice_budgets_equal':results['centralized']['training_slice_draws']==draws,'client_foreground_fraction':{c:float(torch.cat([y[e] for e in ids]).mean()) for c,ids in clients.items()},'clinical_ready':False,'active_model_changed':False,'elapsed_seconds':time.time()-started,'limitations':['One seed; four reused development-validation patients','Simulated clients from a single dataset, not a multi-hospital study','Central and federated total slice draws match; local-only sees half the data','No differential privacy, secure aggregation, Byzantine robustness or transport security','Weights can leak training information; no real participant data is transmitted']}
    save(out/'summary.json',summary)
    table=''.join(f'<tr><td>{name}</td><td>{r["evaluation"]["mean_dice"]:.4f}</td><td>{r["evaluation"]["by_simulated_client"]["client-a"]:.4f}</td><td>{r["evaluation"]["by_simulated_client"]["client-b"]:.4f}</td></tr>' for name,r in results.items())
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Federated simulation</title><style>body{font:18px system-ui;max-width:1000px;margin:40px auto}td,th{padding:12px}</style><h1>Local federated simulation</h1><p>Two simulated clients; no network exchange or privacy guarantee. One seed, two rounds, four development-validation patients. Exact round recovery and saved-model metrics verified.</p><table><tr><th>Model</th><th>Mean Dice</th><th>Client A validation</th><th>Client B validation</th></tr>'+table+'</table><p><a href="summary.json">Results and limitations</a> · <a href="protocol.json">Fixed protocol</a></p>',encoding='utf-8')
    print(json.dumps({'round_recovery_exact':recovery,'results':{k:v['evaluation']['mean_dice'] for k,v in results.items()}}),flush=True)

if __name__=='__main__':main()
