"""Train a CT baseline only from an audited local import; no holdout access."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader,Dataset
from neurofusion.ct_model import HemorrhageCNN
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.specialist_inputs import HEMORRHAGE_LABELS

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=5);args=parser.parse_args()
    if args.output.exists() or not 1<=args.epochs<=100:parser.error('Fresh output and 1-100 epochs required')
    manifest=json.loads(args.manifest.read_text());root=args.manifest.parent.resolve()
    if manifest['labels']!=list(HEMORRHAGE_LABELS):raise ValueError('Wrong target order')
    groups={}
    for row in manifest['records']:
        if row['partition'] not in ('train','validation','holdout'):raise ValueError('Unexpected role')
        old=groups.setdefault(row['patient_group'],row['partition'])
        if old!=row['partition']:raise ValueError('Patient leakage')
    rows={role:[r for r in manifest['records'] if r['partition']==role] for role in ('train','validation')}
    if any(len({r['patient_group'] for r in cohort})<2 for cohort in rows.values()):raise ValueError('At least two patients in each development role required; not sufficient for qualification')
    for cohort in rows.values():
        for row in cohort:
            p=(root/row['array']).resolve()
            if not p.is_relative_to(root) or digest(p)!=row['array_sha256']:raise ValueError('Prepared data changed')
            x=np.load(p,allow_pickle=False)
            if x.shape!=(3,128,128) or not np.isfinite(x).all() or x.min()<0 or x.max()>1:raise ValueError('Invalid CT windows')
            if len(row['labels'])!=6 or not np.isin(row['labels'],[0,1]).all():raise ValueError('Invalid targets')
    class CTData(Dataset):
        def __init__(self,cohort):self.cohort=cohort
        def __len__(self):return len(self.cohort)
        def __getitem__(self,i):
            row=self.cohort[i];return torch.from_numpy(np.load(root/row['array'],allow_pickle=False).astype(np.float32)),torch.tensor(row['labels'],dtype=torch.float32)
    args.output.mkdir();torch.manual_seed(42);torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    device='cuda' if torch.cuda.is_available() else 'cpu';model=HemorrhageCNN().to(device)
    save_json(args.output/'protocol.json',{'manifest_sha256':digest(args.manifest),'seed':42,'epochs':args.epochs,'lr':.001,
        'selection':'final epoch','threshold':.5,'loss':'unweighted BCE; all class supports reported','holdout_used':False,'independently_qualified':False})
    optimizer=torch.optim.Adam(model.parameters(),lr=.001);history=[]
    for epoch in range(args.epochs):
        model.train();losses=[]
        for x,y in DataLoader(CTData(rows['train']),batch_size=32,shuffle=True):
            optimizer.zero_grad();loss=torch.nn.functional.binary_cross_entropy_with_logits(model(x.to(device)),y.to(device));loss.backward();optimizer.step();losses.append(loss.item())
        history.append({'epoch':epoch+1,'loss':float(np.mean(losses))})
    torch.save({'model':model.state_dict(),'epoch':args.epochs,'labels':list(HEMORRHAGE_LABELS)},args.output/'last.pt')
    model.eval();predictions=[];targets=[]
    with torch.inference_mode():
        for x,y in DataLoader(CTData(rows['validation']),batch_size=32):predictions.append(model(x.to(device)).sigmoid().cpu().numpy());targets.append(y.numpy())
    p=np.concatenate(predictions);y=np.concatenate(targets);per_class={}
    for i,name in enumerate(HEMORRHAGE_LABELS):
        truth=y[:,i]>0;pred=p[:,i]>=.5;tp=int((truth&pred).sum());fn=int((truth&~pred).sum());fp=int((~truth&pred).sum());tn=int((~truth&~pred).sum())
        per_class[name]={'tp':tp,'fn':fn,'fp':fp,'tn':tn,'sensitivity':tp/(tp+fn) if tp+fn else None,'specificity':tn/(tn+fp) if tn+fp else None}
    np.savez_compressed(args.output/'validation.npz',probabilities=p,targets=y)
    save_json(args.output/'summary.json',{'history':history,'per_class':per_class,'cases':[r['image_id'] for r in rows['validation']],
        'any_subtype_inconsistencies':int(np.sum((p[:,5]>=.5)!=(p[:,:5]>=.5).any(1))),
        'checkpoint_sha256':digest(args.output/'last.pt'),'holdout_used':False,'independently_qualified':False,'promotion_permitted':False,
        'limitations':'Slice-level development baseline; no localization/segmentation or independent validation. Rare-class support may be absent.'})

if __name__=='__main__':main()
