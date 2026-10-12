"""Real-checkpoint communication/recovery replay and fixed development evaluation."""
import argparse,json
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.federated_exchange import RoundExchange
from neurofusion.tumor_segmentation import TumorUNet,segmentation_loss


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];old=root/'experiments/federated-simulation-001';out=a.output;out.mkdir(parents=True,exist_ok=False)
    read=lambda p:json.loads(p.read_text());plan=read(old/'protocol.json');prior=read(old/'summary.json');provenance=read(old/'provenance.json')
    cache=root/'experiments/ucsf-specialist-cache-001';partpath=root/'experiments/ucsf-specialist-plan-001/partitions.json';parts=read(partpath);manifest=read(cache/'manifest.json')
    if digest(partpath)!=provenance['partitions'] or digest(cache/'manifest.json')!=provenance['cache']:raise ValueError('Frozen data sources changed')
    clients=plan['client_training_patients'];valclients=plan['client_validation_patients'];validation=sorted(parts['development_validation_patients'])
    train=[patient for values in clients.values() for patient in values];val=[patient for values in valclients.values() for patient in values]
    protected={r['patient_id'] for r in read(root/'experiments/ucsf-acquisition-001/summary.json')['results']}
    if len(set(train))!=16 or len(train)!=16 or set(train)!=set(parts['train_patients']) or set(val)!=set(validation) or len(val)!=4 or set(train)&set(val) or (set(train)|set(val))&protected:raise ValueError('Patient split or protected exclusion differs')
    save_json(out/'protocol.json',dict(original_protocol_sha256=digest(old/'protocol.json'),
        scope='Repeat historical round two, persist actual client messages, reopen after partial delivery, verify committed recovery and all four development evaluations',
        threshold=.5,untouched_evaluation=False,protected_cohort_used=False,network_transport=False,
        checkpoints={arm:r['checkpoint_sha256'] for arm,r in prior['arms'].items()},
        source_hashes={str(path.relative_to(root)):digest(path) for path in [Path(__file__),root/'src/neurofusion/federated_exchange.py',root/'src/neurofusion/federated.py']}))
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    if not torch.cuda.is_available():raise ValueError('CUDA required to reproduce original round training')
    x={};y={};sources={r['exam_id']:r for r in parts['records']}
    for r in manifest['cases']:
        source=sources[r['exam_id']];directory=cache/r['directory']
        if r['role']!=source['role'] or r['patient_id']!=source['patient_id']:raise ValueError('Role mismatch')
        for name,sha in r['sha256'].items():
            if digest(directory/name)!=sha:raise ValueError('Cache changed')
        for k in ('image','mask'):
            if digest(root/'data/raw/ucsf-pdgm-v5'/source[k]['path'])!=source[k]['sha256']:raise ValueError('Raw development source changed')
        x[r['exam_id']]=F.interpolate(torch.from_numpy(np.load(directory/'images.npy').astype(np.float32)/255),size=(120,120),mode='bilinear',align_corners=False)
        y[r['exam_id']]=F.interpolate(torch.from_numpy(np.load(directory/'targets.npy').astype(np.float32)),size=(120,120),mode='nearest')
    roundpath=old/'round-1.pt';expected=prior['arms']['federated']['rounds'][0]['sha256']
    if digest(roundpath)!=expected:raise ValueError('Round-one checkpoint changed')
    recovered=torch.load(roundpath,weights_only=True,map_location='cpu')
    if recovered['round']!=1 or recovered['protocol_sha256']!=digest(old/'protocol.json'):raise ValueError('Recovery metadata differs')
    counts={c:sum(len(x[e]) for e in exams) for c,exams in clients.items()}
    exchange=RoundExchange.create(out/'round-2',recovered['state'],2,digest(old/'protocol.json'),counts)
    missing_rejected=False;identical_retry=False
    for index,(client,exams) in enumerate(clients.items()):
        seed=440+index;torch.manual_seed(seed);model=TumorUNet().cuda();model.load_state_dict(recovered['state']);optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        xx=torch.cat([x[e] for e in exams]);yy=torch.cat([y[e] for e in exams])
        for batch in torch.randperm(len(xx),generator=torch.Generator().manual_seed(seed)).split(16):
            optimizer.zero_grad(set_to_none=True);loss=segmentation_loss(model(xx[batch].cuda()),yy[batch].cuda());loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step()
        state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};payload=exchange.encode(client,state)
        exchange.submit(payload)
        if index==0:
            try:exchange.finish()
            except ValueError as e:
                if 'incomplete' not in str(e):raise
                missing_rejected=True
            exchange=RoundExchange(out/'round-2');identical_retry=exchange.submit(payload)=='identical_retry'
        print('Persisted and checked',client,len(payload),'bytes',flush=True)
    final=exchange.finish();again=RoundExchange(out/'round-2').finish()
    historical=torch.load(old/'federated.pt',weights_only=True,map_location='cpu')
    if not all(torch.equal(final[k],historical[k]) and torch.equal(again[k],historical[k]) for k in historical):raise ValueError('Recovered aggregate differs from original')
    evaluations={}
    for arm,record in prior['arms'].items():
        path=old/(arm+'.pt')
        if digest(path)!=record['checkpoint_sha256']:raise ValueError('Evaluation checkpoint changed')
        model=TumorUNet().cuda();model.load_state_dict(torch.load(path,weights_only=True,map_location='cpu'));model.eval();scores=[]
        with torch.inference_mode():
            for exam in validation:
                pred=torch.cat([model(b.cuda()).sigmoid().cpu()>=.5 for b in x[exam].split(16)]);truth=y[exam]>0;den=int(pred.sum()+truth.sum())
                scores.append(dict(exam=exam,dice=2*int((pred&truth).sum())/den if den else 1.))
        evaluation=dict(cases=scores,mean_dice=float(np.mean([r['dice'] for r in scores])),by_simulated_client={c:float(np.mean([r['dice'] for r in scores if r['exam'] in ids])) for c,ids in valclients.items()})
        if evaluation!=record['evaluation']:raise ValueError('Saved development metrics differ')
        evaluations[arm]=evaluation
        print('Reproduced',arm,evaluation['mean_dice'],flush=True)
    expected_draws=sum(counts.values())*2
    if prior['arms']['centralized']['training_slice_draws']!=expected_draws or prior['arms']['federated']['training_slice_draws']!=expected_draws:raise ValueError('Comparison training budgets differ')
    communication=read(out/'round-2/commit.json')
    save_json(out/'summary.json',dict(passed=True,missing_client_rejected=missing_rejected,identical_retry_idempotent=identical_retry,
        partial_delivery_recovery_exact=True,committed_recovery_exact=True,historical_global_weights_exact=True,
        communication=communication,evaluations=evaluations,central_and_federated_draws=expected_draws,
        training_patients=16,development_validation_patients=4,protected_cohort_used=False,
        untouched_evaluation_complete=False,independently_qualified=False,active_model_changed=False,
        limitation='Local serialized-message simulation; no real network, authentication, privacy or multi-hospital validation'))
    print('Federated system verification passed')


if __name__=='__main__':main()
