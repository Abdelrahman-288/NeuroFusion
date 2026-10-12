"""Recompute saved development predictions and check paired annotation/training budgets."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from neurofusion.external_import import digest
from neurofusion.active_learning import select_annotations
from neurofusion.tumor_segmentation import TumorUNet

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    summary=read(a.run/'summary.json');protocol=read(a.run/'protocol.json');cache=ROOT/'experiments/ucsf-specialist-cache-001'
    if digest(a.run/'protocol.json')!=summary['protocol_sha256']:raise ValueError('Protocol changed')
    cases={r['exam_id']:r for r in read(cache/'manifest.json')['cases']};torch.set_num_threads(4);checked=[]
    for seed in summary['seeds']:
        folder=a.run/f'seed-{seed["seed"]}';candidate=read(folder/'candidates.json');selection=read(folder/'selection.json')
        if digest(folder/'seed-model.pt')!={r['model_sha256'] for r in candidate['records']}.pop():raise ValueError('Selection model mismatch')
        replay=select_annotations(candidate['records'],protected_patients=protocol['protected_patients'],budget=4,seed=seed['seed'])
        if replay!=selection:raise ValueError('Selection not reproducible')
        counts=[]
        for arm,result in seed['arms'].items():
            chosen=result['selected'];counts.append((len(chosen),result['training_draws'],result['optimizer_updates']))
            expected=[r['case_id'] for r in selection['selected']] if arm=='active' else selection['random_comparator_case_ids']
            if chosen!=expected or set(chosen)&set(seed['initial_patients']) or not set(chosen)<=set(seed['pool']):raise ValueError('Invalid budget/selection')
            if (set(chosen)|set(seed['initial_patients']))&set(protocol['protected_patients']):raise ValueError('Protected exposure')
            path=folder/(arm+'.pt')
            if digest(path)!=result['checkpoint_sha256']:raise ValueError('Checkpoint changed')
            model=TumorUNet().cuda();model.load_state_dict(torch.load(path,weights_only=True,map_location='cuda'));model.eval()
            for expected_score in result['evaluation']['cases']:
                case=cases[expected_score['exam_id']];directory=cache/case['directory']
                for name in ('images.npy','targets.npy'):
                    if digest(directory/name)!=case['sha256'][name]:raise ValueError('Cache changed')
                x=F.interpolate(torch.from_numpy(np.load(directory/'images.npy').astype(np.float32)/255),size=(120,120),mode='bilinear',align_corners=False)
                y=F.interpolate(torch.from_numpy(np.load(directory/'targets.npy').astype(np.float32)),size=(120,120),mode='nearest')>0
                with torch.inference_mode():prediction=torch.cat([model(b.cuda()).sigmoid().cpu()>=.5 for b in x.split(16)])
                denominator=int(prediction.sum()+y.sum());dice=2*int((prediction&y).sum())/denominator if denominator else 1.
                if abs(dice-expected_score['dice'])>1e-6:raise ValueError('Metric replay differs')
                checked.append({'seed':seed['seed'],'arm':arm,'exam':case['exam_id'],'dice':dice})
            del model
        if counts[0]!=counts[1] or counts[0][0]!=4:raise ValueError('Unequal budget or compute')
    result={'passed':True,'paired_seeds':len(summary['seeds']),'checkpoint_patient_predictions_reproduced':len(checked),'equal_patient_and_training_budgets':True,'selection_reproduced':True,'human_effort_verified':False,'checks':checked}
    (a.run/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='checks'}))

if __name__=='__main__':main()
