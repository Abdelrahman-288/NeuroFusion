"""Retrospective equal-patient-budget segmentation benchmark, development data only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch.nn import functional as F
from neurofusion.active_learning import select_annotations
from neurofusion.external_import import digest
from neurofusion.tumor_segmentation import TumorUNet, segmentation_loss

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def split_train(records,seed):
    train=[r for r in records if r['role']=='train']
    ordered=sorted(train,key=lambda r:hashlib.sha256(f"initial:{seed}:{r['patient_id']}".encode()).hexdigest())
    if len({r['patient_id'] for r in records})!=len(records):raise ValueError('Repeated patient')
    return ordered[:4],ordered[4:]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    cache=ROOT/'experiments/ucsf-specialist-cache-001';part_path=ROOT/'experiments/ucsf-specialist-plan-001/partitions.json'
    manifest=read(cache/'manifest.json');parts=read(part_path);rows=parts['records'];sources={r['exam_id']:r for r in rows}
    if manifest['partitions_sha256']!=digest(part_path):raise ValueError('Partition hash mismatch')
    protected=parts['development_validation_patients']+[r['patient_id'] for r in read(ROOT/'experiments/ucsf-acquisition-001/summary.json')['results']]
    if set(parts['train_patients'])&set(protected):raise ValueError('Protected patient overlap')
    plan={'kind':'retrospective_label_reveal','seeds':[42,43,44],'initial_patients':4,'pool_patients':12,'additional_patients_per_arm':4,'final_patients_per_arm':8,'epochs':3,'batch_size':16,'learning_rate':.001,'size':120,'threshold':.5,'diversity_weight':.5,'metric':'mean patient Dice on downsampled 120x120 development-validation grid','validation_patients':parts['development_validation_patients'],'protected_patients':protected,'label_cost':'one complete patient volume; not annotation minutes','checkpoint':'fixed final epoch','initialization':'paired identical random initialization, retrain each arm from scratch','clinical_ready':False,'human_annotation_experiment':False,'limitations':['Existing labels revealed retrospectively; no new expert annotation','Four repeatedly used development-validation patients; not independent evaluation','Equal patient count does not imply equal annotation time','Labels affect training only after a case is selected; cache integrity reads are not model inputs']}
    save(out/'protocol.json',plan);save(out/'partitions.json',parts)
    save(out/'provenance.json',{'partition_sha256':digest(part_path),'cache_manifest_sha256':digest(cache/'manifest.json'),'runner_sha256':digest(Path(__file__)),'selector_sha256':digest(ROOT/'src/neurofusion/active_learning.py'),'model_source_sha256':digest(ROOT/'src/neurofusion/tumor_segmentation.py')})
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    images={};case_rows={r['exam_id']:r for r in manifest['cases']}
    for case in manifest['cases']:
        exam=case['exam_id'];row=sources[exam]
        if case['patient_id']!=row['patient_id'] or case['role']!=row['role']:raise ValueError('Role mismatch')
        directory=cache/case['directory']
        for name,checksum in case['sha256'].items():
            if digest(directory/name)!=checksum:raise ValueError('Cache checksum mismatch')
        for key in ('image','mask'):
            if digest(ROOT/'data/raw/ucsf-pdgm-v5'/row[key]['path'])!=row[key]['sha256']:raise ValueError('Source hash mismatch')
        x=torch.from_numpy(np.load(directory/'images.npy').astype(np.float32)/255)
        images[exam]=F.interpolate(x,size=(120,120),mode='bilinear',align_corners=False)
    def labels(exam):
        array=np.load(cache/case_rows[exam]['directory']/'targets.npy')
        return F.interpolate(torch.from_numpy(array.astype(np.float32)),size=(120,120),mode='nearest')
    def train(exams,initial,seed):
        torch.manual_seed(seed);model=TumorUNet().cuda();model.load_state_dict(initial)
        optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        x=torch.cat([images[e] for e in exams]);y=torch.cat([labels(e) for e in exams]);history=[]
        generator=torch.Generator().manual_seed(seed)
        for epoch in range(3):
            model.train();losses=[]
            for batch in torch.randperm(len(x),generator=generator).split(16):
                optimizer.zero_grad(set_to_none=True);loss=segmentation_loss(model(x[batch].cuda()),y[batch].cuda())
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();losses.append(loss.item())
            history.append(float(np.mean(losses)))
        return model,history,len(x)*3,(len(x)+15)//16*3
    def evaluate(model):
        model.eval();scores=[]
        with torch.inference_mode():
            for exam in parts['development_validation_patients']:
                pred=torch.cat([model(b.cuda()).sigmoid().cpu()>=.5 for b in images[exam].split(16)])
                truth=labels(exam)>0;den=int(pred.sum()+truth.sum());dice=2*int((pred&truth).sum())/den if den else 1.
                scores.append({'exam_id':exam,'dice':dice})
        return {'cases':scores,'mean_dice':float(np.mean([r['dice'] for r in scores]))}
    results=[];started=time.time()
    for seed in plan['seeds']:
        folder=out/f'seed-{seed}';folder.mkdir();initial_rows,pool=split_train(rows,seed)
        if len(pool)!=12:raise ValueError('Unexpected pool size')
        initial_ids=[r['exam_id'] for r in initial_rows];torch.manual_seed(seed);initial=copy.deepcopy(TumorUNet().state_dict())
        baseline,history,_,_=train(initial_ids,initial,seed);torch.save(baseline.state_dict(),folder/'seed-model.pt');model_hash=digest(folder/'seed-model.pt');baseline.eval()
        candidates=[];features=[]
        hook=baseline.bottom.register_forward_hook(lambda module,inputs,output:features.append(output.mean((2,3)).detach().cpu()))
        with torch.inference_mode():
            for row in pool:
                exam=row['exam_id'];features.clear();entropy=[]
                for b in images[exam].split(16):
                    p=baseline(b.cuda()).sigmoid().clamp(1e-6,1-1e-6)
                    entropy.extend((-(p*p.log()+(1-p)*(1-p).log())/np.log(2)).mean((1,2,3)).cpu().tolist())
                candidates.append({'case_id':exam,'patient_id':row['patient_id'],'partition':'train','role':'unlabeled_development','patient_identity_verified':True,'uncertainty':float(np.mean(entropy)),'embedding':torch.cat(features).mean(0).tolist(),'embedding_version':'unet-bottom-mean-120-v1','uncertainty_method':'mean-binary-entropy-v1','model_sha256':model_hash,'input_sha256':row['image']['sha256']})
        hook.remove();selection=select_annotations(candidates,protected_patients=protected,budget=4,seed=seed)
        save(folder/'candidates.json',{'records':candidates,'protected_patients':protected,'budget':4,'seed':seed});save(folder/'selection.json',selection)
        result={'seed':seed,'initial_patients':initial_ids,'pool':[r['exam_id'] for r in pool],'baseline':evaluate(baseline),'arms':{}}
        del baseline
        for arm,chosen in [('active',[r['case_id'] for r in selection['selected']]),('random',selection['random_comparator_case_ids'])]:
            model,history,draws,updates=train(initial_ids+chosen,initial,seed)
            score=evaluate(model);torch.save(model.state_dict(),folder/(arm+'.pt'))
            result['arms'][arm]={'selected':chosen,'annotation_budget_patients':len(chosen),'training_draws':draws,'optimizer_updates':updates,'loss_history':history,'evaluation':score,'checkpoint_sha256':digest(folder/(arm+'.pt'))}
            print(f'Seed {seed} {arm}: Dice {score["mean_dice"]:.5f}',flush=True);del model
        result['paired_difference']=result['arms']['active']['evaluation']['mean_dice']-result['arms']['random']['evaluation']['mean_dice'];results.append(result);save(folder/'result.json',result)
    summary={'protocol_sha256':digest(out/'protocol.json'),'benchmark_completed':True,'human_annotation_experiment_completed':False,'active_model_changed':False,'seeds':results,'mean_active_dice':float(np.mean([r['arms']['active']['evaluation']['mean_dice'] for r in results])),'mean_random_dice':float(np.mean([r['arms']['random']['evaluation']['mean_dice'] for r in results])),'mean_paired_difference':float(np.mean([r['paired_difference'] for r in results])),'elapsed_seconds':time.time()-started,'device':torch.cuda.get_device_name(),'torch_version':torch.__version__,'limitations':plan['limitations']}
    save(out/'summary.json',summary)
    table=''.join(f'<tr><td>{r["seed"]}</td><td>{r["arms"]["active"]["evaluation"]["mean_dice"]:.4f}</td><td>{r["arms"]["random"]["evaluation"]["mean_dice"]:.4f}</td><td>{r["paired_difference"]:+.4f}</td></tr>' for r in results)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Active learning benchmark</title><style>body{font:18px system-ui;max-width:1000px;margin:40px auto;background:#102030;color:#eee}td,th{padding:15px}a{color:#8ed}</style><h1>Equal-budget development benchmark</h1><p>4 initial patients + 4 selected patients per arm; 12-patient candidate pool; 3 paired seeds. Fixed 3 epochs, 120-pixel grid, four development-validation patients.</p><table><tr><th>Seed</th><th>Active Dice</th><th>Random Dice</th><th>Difference</th></tr>'+table+'<p>Retrospective supplied-label reveal. No human annotation-time savings or independent clinical performance established. Protected new UCSF cohort was not scored or trained on.</p><a href="summary.json">Results</a> · <a href="protocol.json">Fixed protocol</a>',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='seeds'}),flush=True)

if __name__=='__main__':main()
