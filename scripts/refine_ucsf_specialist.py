"""Fixed three-seed refinement of stabilized UCSF development checkpoints."""
import argparse
import json
from pathlib import Path
import random
import numpy as np
import nibabel as nib
import torch
from torch.utils.data import DataLoader
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.ucsf_loader import UCSFSlices
from neurofusion.ucsf_validation import score_native,aggregate_cases
from neurofusion.tumor_segmentation import TumorUNet,segmentation_loss
from neurofusion.ucsf_confirmation import confirm_pairs

ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(p.read_text())


def evaluate(model,val,manifest,records,source,cache,output=None):
    cases=[]
    model.eval()
    with torch.inference_mode():
        for case,(images,_) in zip([c for c in manifest['cases'] if c['role']=='development_validation'],val.arrays):
            probabilities=[]
            for z in range(0,len(images),8):
                x=torch.from_numpy(images[z:z+8].astype(np.float32)/255).cuda()
                with torch.autocast('cuda',dtype=torch.float16):logits=model(x)
                probabilities.append(logits.float().sigmoid().cpu().numpy()[:,0])
            reference=nib.load(source/records[case['exam_id']]['mask']['path'])
            metrics,prediction=score_native(np.concatenate(probabilities),read(cache/case['directory']/'geometry.json'),reference)
            cases.append(dict(exam_id=case['exam_id'],patient_id=case['patient_id'],metrics=metrics))
            if output is not None:nib.save(prediction,output/(case['exam_id']+'-prediction.nii.gz'))
    return dict(cases=cases,aggregate=aggregate_cases(cases))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    if not torch.cuda.is_available():raise RuntimeError('Existing CUDA environment required')
    torch.set_num_threads(2);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    cache=ROOT/'experiments/ucsf-specialist-cache-001';partition=ROOT/'experiments/ucsf-specialist-plan-001/partitions.json'
    manifest=read(cache/'manifest.json');parts=read(partition);source=ROOT/'data/raw/ucsf-pdgm-v5'
    if manifest['partitions_sha256']!=digest(partition):raise ValueError('Partition changed')
    records={r['exam_id']:r for r in parts['records']}
    for case in manifest['cases']:
        row=records[case['exam_id']]
        if any(row[k]!=case[k] for k in ('patient_id','role','slices')):raise ValueError('Role mismatch')
        for key in ('image','mask'):
            path=(source/row[key]['path']).resolve()
            if not path.is_relative_to(source.resolve()) or digest(path)!=row[key]['sha256']:raise ValueError('Source changed')
    controls={str(s):ROOT/'experiments'/f'ucsf-clipping-seed{s}-{"002" if s==44 else "001"}' for s in (42,43,44)}
    hashes={s:digest(folder/'epoch-05.pt') for s,folder in controls.items()}
    for s,folder in controls.items():
        if hashes[s]!=read(folder/'summary.json')['checkpoints']['epoch-05.pt']:raise ValueError('Control checkpoint changed')
    protocol=dict(seeds=[42,43,44],initial_checkpoints=hashes,epochs=5,learning_rate=.0003,
        optimizer='Adam reset; fixed lower-rate refinement from stabilized epoch 5',
        batch_size=8,gradient_clip=1.,mixed_precision=True,sampling='uniform without replacement',
        loss='unchanged BCE plus per-image soft Dice',threshold=.5,selection='final epoch only',
        comparator='paired stabilized/clipped epoch-5 controls; original failed unclipped comparisons remain failed',
        acceptance='All four existing relative checks in every seed, plus no newly zero-Dice patient',
        partitions_sha256=digest(partition),cache_manifest_sha256=digest(cache/'manifest.json'),
        source_sha256=digest(Path(__file__)),protected_cohort_used=False,independent=False,promotion_permitted=False)
    save_json(a.output/'protocol.json',protocol)
    train=UCSFSlices(cache,'train');val=UCSFSlices(cache,'development_validation');pairs={};verifications=[]
    for seed in (42,43,44):
        out=a.output/f'seed{seed}';out.mkdir();random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        generator=torch.Generator().manual_seed(seed)
        loader=DataLoader(train,batch_size=8,shuffle=True,generator=generator,num_workers=0)
        checkpoint=torch.load(controls[str(seed)]/'epoch-05.pt',map_location='cpu',weights_only=True)
        model=TumorUNet().cuda();model.load_state_dict(checkpoint['model_state_dict'])
        optimizer=torch.optim.Adam(model.parameters(),lr=.0003);scaler=torch.amp.GradScaler('cuda');history=[]
        for epoch in range(1,6):
            model.train();total=0.;seen=set();skipped=0
            for batch in loader:
                x,y=batch['image'].cuda(),batch['target'].cuda();optimizer.zero_grad(set_to_none=True)
                seen.update(zip(batch['exam_id'],batch['canonical_z'].tolist()))
                with torch.autocast('cuda',dtype=torch.float16):loss=segmentation_loss(model(x),y)
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                scaler.scale(loss).backward();scaler.unscale_(optimizer)
                finite=all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
                if finite:torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
                else:skipped+=1
                scaler.step(optimizer);scaler.update();total+=loss.item()*len(x)
            if len(seen)!=len(train):raise ValueError('Incomplete training coverage')
            result=evaluate(model,val,manifest,records,source,cache,out if epoch==5 else None)
            history.append(dict(epoch=epoch,train_loss=total/len(train),unique_slices=len(seen),skipped_updates=skipped,**result))
            save_json(out/'history.json',history)
            torch.save(dict(model_state_dict=model.state_dict(),epoch=epoch,optimizer_state_dict=optimizer.state_dict(),
                scaler_state_dict=scaler.state_dict(),protocol_sha256=digest(a.output/'protocol.json')),out/f'epoch-{epoch:02d}.pt')
            print(f'Seed {seed} refinement epoch {epoch}/5 Dice {result["aggregate"]["dice"]["mean"]:.5f}',flush=True)
        final=dict(final_epoch=history[-1],completed_epochs=5,seed=seed,active_model_changed=False)
        save_json(out/'summary.json',final)
        reloaded=TumorUNet().cuda();reloaded.load_state_dict(torch.load(out/'epoch-05.pt',map_location='cpu',weights_only=True)['model_state_dict'])
        replay=evaluate(reloaded,val,manifest,records,source,cache)
        if replay['cases']!=history[-1]['cases']:raise ValueError('Reload metrics differ')
        verifications.append(dict(seed=seed,checkpoint_sha256=digest(out/'epoch-05.pt'),metrics_reproduced=True))
        pairs[seed]=(read(controls[str(seed)]/'summary.json'),final)
    comparisons=confirm_pairs(pairs)
    for seed,result in comparisons['seeds'].items():
        newly=[r['patient_id'] for r in result['patients'] if r['baseline_dice']>0 and r['candidate_dice']==0]
        result['newly_zero_dice_patients']=newly
        result['gates']['no_new_zero_dice_patients']=not newly
        result['all_passed']=all(result['gates'].values())
    comparisons['all_seeds_passed']=all(r['all_passed'] for r in comparisons['seeds'].values())
    comparisons['decision']='passes new development comparison only' if comparisons['all_seeds_passed'] else 'reject refinement; retain current models'
    comparisons.update(independent=False,original_qualification_passed=False,model_promoted=False,
        verification=verifications,protocol_sha256=digest(a.output/'protocol.json'))
    save_json(a.output/'summary.json',comparisons)
    print(json.dumps(comparisons,indent=2),flush=True)


if __name__=='__main__':main()
