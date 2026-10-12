"""Five-epoch UCSF engineering baseline; never promotes a clinical model."""
import argparse
import hashlib
import json
import platform
import random
import time
from pathlib import Path
import nibabel as nib
import numpy as np
import torch
from torch.utils.data import DataLoader
from neurofusion.ucsf_loader import UCSFSlices
from neurofusion.tumor_segmentation import TumorUNet, segmentation_loss
from neurofusion.ucsf_validation import score_native, aggregate_cases


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path, value): Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--seed',type=int,choices=[42,43,44],default=42)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--balanced', action='store_true')
    group.add_argument('--low-lr', action='store_true')
    group.add_argument('--clip-grad',action='store_true')
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    cache=root/'experiments/ucsf-specialist-cache-001'
    partition=root/'experiments/ucsf-specialist-plan-001/partitions.json'
    protocol=root/'experiments/ucsf-specialist-train-002/protocol.json'
    plan=read(protocol); parts=read(partition); manifest=read(cache/'manifest.json')
    if manifest['partitions_sha256']!=digest(partition): raise ValueError('Partition checksum mismatch')
    config=plan['training_plan']
    if config!={'seed':42,'epochs':5,'batch_size':8,'optimizer':'Adam','learning_rate':0.001,'loss':'BCE plus soft Dice','augmentation':'none','mixed_precision':True}: raise ValueError('Unsupported protocol')
    config['seed']=a.seed
    if a.low_lr:
        low_lr_path=root/'configs/ucsf_low_lr_protocol.json'
        low_lr=read(low_lr_path)
        if low_lr['baseline_learning_rate']!=.001 or low_lr['candidate_learning_rate']!=.0003:raise ValueError('Unexpected learning rate protocol')
        config['learning_rate']=low_lr['candidate_learning_rate']
    if a.clip_grad:
        clip_path=root/'configs/ucsf_clipping_confirmation_protocol.json'
        clip_plan=read(clip_path)
        if clip_plan['max_norm']!=1.0 or a.seed not in clip_plan['seeds']:raise ValueError('Unsupported clipping plan')
        config['gradient_clip_norm']=1.0
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
    records={r['exam_id']:r for r in parts['records']}
    if len(records)!=len(manifest['cases']): raise ValueError('Case inventory mismatch')
    source=root/'data/raw/ucsf-pdgm-v5'
    for case in manifest['cases']:
        row=records[case['exam_id']]
        if any(row[k]!=case[k] for k in ('patient_id','role','slices')): raise ValueError('Case partition mismatch')
        for key in ('image','mask'):
            path=(source/row[key]['path']).resolve()
            if not path.is_relative_to(source) or digest(path)!=row[key]['sha256']: raise ValueError('Source checksum mismatch')
    train=UCSFSlices(cache,'train'); val=UCSFSlices(cache,'development_validation')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    if a.clip_grad:write(out/'clipping-protocol.json',clip_plan)
    if a.low_lr:write(out/'experiment-protocol.json',low_lr)
    if a.balanced:
        sampling_protocol=root/'configs/ucsf_balanced_sampling_protocol.json'
        sampling=read(sampling_protocol)
        if sampling['sampling']!={'positive_slice_probability':0.5,'negative_slice_probability':0.5,'within_group':'uniform with replacement','draws_per_epoch':2480,'training_only':True}:raise ValueError('Unsupported sampling protocol')
        write(out/'sampling-protocol.json',sampling)
    write(out/'protocol.json',plan);write(out/'partitions.json',parts);write(out/'cache-manifest.json',manifest)
    provenance={str(path.relative_to(root)):digest(path) for path in [protocol,partition,cache/'manifest.json',Path(__file__),root/'src/neurofusion/ucsf_validation.py',root/'src/neurofusion/ucsf_loader.py',root/'src/neurofusion/tumor_segmentation.py',root/'src/neurofusion/external_adapter.py',root/'src/neurofusion/native_metrics.py']}
    if a.balanced:
        for path in (sampling_protocol,root/'src/neurofusion/ucsf_sampling.py'):
            provenance[str(path.relative_to(root))]=digest(path)
    if a.low_lr:provenance[str(low_lr_path.relative_to(root))]=digest(low_lr_path)
    if a.clip_grad:
        for path in (clip_path,root/'src/neurofusion/gradient_control.py'):
            provenance[str(path.relative_to(root))]=digest(path)
    snapshots=out/'source';snapshots.mkdir()
    for name in provenance:
        if name.endswith('.py'): (snapshots/Path(name).name).write_bytes((root/name).read_bytes())
    write(out/'provenance.json',provenance)
    random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    generator=torch.Generator().manual_seed(a.seed)
    if a.balanced:
        from neurofusion.ucsf_sampling import foreground_weights
        weights,flags=foreground_weights(train)
        sampler=torch.utils.data.WeightedRandomSampler(weights,len(train),replacement=True,generator=generator)
        loader=DataLoader(train,batch_size=8,sampler=sampler,generator=generator,num_workers=0)
        write(out/'sampling.json',{'positive_slices':int(flags.sum()),'negative_slices':int((~flags).sum()),'expected_positive_probability':float(weights[flags].sum()),'draws_per_epoch':len(train),'replacement':True})
    else:
        loader=DataLoader(train,batch_size=8,shuffle=True,generator=generator,num_workers=0)
    model=TumorUNet().cuda();optimizer=torch.optim.Adam(model.parameters(),lr=config['learning_rate'])
    scaler=torch.amp.GradScaler('cuda');history=[];start=time.time()
    torch.cuda.reset_peak_memory_stats()
    for epoch in range(1,6):
        model.train();total=0;skipped_updates=0;positive_draws=0;unique_draws=set();clipped_updates=0;max_post_clip=0.0
        for step,b in enumerate(loader,1):
            positive_draws+=int(b['target'].flatten(1).any(dim=1).sum())
            unique_draws.update(zip(b['exam_id'],b['canonical_z'].tolist()))
            x,y=b['image'].cuda(),b['target'].cuda();optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.float16): loss=segmentation_loss(model(x),y)
            if not torch.isfinite(loss): raise RuntimeError('Nonfinite loss')
            scaler.scale(loss).backward();scaler.unscale_(optimizer)
            finite_gradients=all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
            if not finite_gradients: skipped_updates+=1
            if a.clip_grad and finite_gradients:
                from neurofusion.gradient_control import clip_unscaled_gradients
                before_norm,after_norm=clip_unscaled_gradients(model.parameters(),1.0)
                clipped_updates+=int(before_norm>1.0);max_post_clip=max(max_post_clip,after_norm)
                if after_norm>1.00001:raise RuntimeError('Gradient bound violated')
            # GradScaler skips overflowing updates and reduces its scale automatically.
            scaler.step(optimizer);scaler.update();total+=loss.item()*len(x)
            if step%100==0: print(f'Epoch {epoch}/5 batch {step}/{len(loader)}',flush=True)
        model.eval();cases=[]
        with torch.inference_mode():
            selected=[c for c in manifest['cases'] if c['role']=='development_validation']
            for case,(images,_) in zip(selected,val.arrays):
                probabilities=[]
                for z in range(0,len(images),8):
                    x=torch.from_numpy(images[z:z+8].astype(np.float32)/255).cuda()
                    with torch.autocast('cuda',dtype=torch.float16): logits=model(x)
                    probabilities.append(logits.float().sigmoid().cpu().numpy()[:,0])
                geometry=read(cache/case['directory']/'geometry.json')
                reference=nib.load(source/records[case['exam_id']]['mask']['path'])
                metrics,prediction=score_native(np.concatenate(probabilities),geometry,reference)
                cases.append({'exam_id':case['exam_id'],'patient_id':case['patient_id'],'metrics':metrics})
                if epoch==5: nib.save(prediction,out/(case['exam_id']+'-prediction.nii.gz'))
        row={'epoch':epoch,'clipped_updates':clipped_updates,'max_post_clip_gradient_l2':max_post_clip,'positive_draws':positive_draws,'negative_draws':len(train)-positive_draws,'unique_slice_draws':len(unique_draws),'optimizer_updates':len(loader)-skipped_updates,'overflow_skipped_updates':skipped_updates,'gradient_scale':scaler.get_scale(),'train_loss':total/len(train),'cases':cases,'aggregate':aggregate_cases(cases)}
        history.append(row);write(out/'history.json',history)
        checkpoint=out/f'epoch-{epoch:02d}.pt'
        torch.save({'epoch':epoch,'model_state_dict':model.state_dict(),'optimizer_state_dict':optimizer.state_dict(),'scaler_state_dict':scaler.state_dict(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),'loader_rng':generator.get_state(),'protocol_sha256':digest(out/'protocol.json'),'provenance':provenance},checkpoint)
        print(f'Epoch {epoch}: loss={row["train_loss"]:.5f}, development native Dice={row["aggregate"]["dice"]["mean"]:.5f}',flush=True)
    result={'purpose':'Engineering development only; numeric annotation union, not clinical evaluation',
        'seed':a.seed,'learning_rate':config['learning_rate'],
        'sampling_mode':'balanced_with_replacement' if a.balanced else 'uniform_without_replacement',
        'completed_epochs':5,'train_patients':16,'development_validation_patients':4,'test_patients':0,
        'train_slices':len(train),'validation_slices':len(val),'final_epoch':history[-1],
        'checkpoint_selection':'predeclared final epoch, not best validation epoch','active_model_changed':False,
        'device':torch.cuda.get_device_name(),'torch_version':torch.__version__,'python_version':platform.python_version(),
        'elapsed_seconds':time.time()-start,'peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,
        'checkpoints':{f'epoch-{i:02d}.pt':digest(out/f'epoch-{i:02d}.pt') for i in range(1,6)},
        'limitations':plan['limits'][:4]}
    write(out/'summary.json',result)
    rows=''.join(f'<tr><td>{h["epoch"]}</td><td>{h["train_loss"]:.4f}</td><td>{h["aggregate"]["dice"]["mean"]:.4f}</td><td>{h["aggregate"]["iou"]["mean"]:.4f}</td></tr>' for h in history)
    patientrows=''.join(f'<tr><td>{c["exam_id"]}</td><td>{c["metrics"]["dice"]:.4f}</td><td>{c["metrics"]["reference_ml"]:.2f}</td><td>{c["metrics"]["prediction_ml"]:.2f}</td></tr>' for c in cases)
    (out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>UCSF engineering baseline</title><style>body{font:17px system-ui;background:#0e1b2b;color:#edf4ff;max-width:1000px;margin:40px auto;padding:20px}td,th{padding:12px;border-bottom:1px solid #456}a{color:#65ded0}</style><h1>UCSF specialist: five epochs complete</h1><p>Numeric annotation foreground from T1c MRI. Research engineering experiment; not a diagnostic model.</p><p>16 training patients / 4 development-validation patients / no independent test patients. All 20 previously used in preprocessing QA. Final epoch selected in advance; active application models unchanged.</p><h2>Learning history</h2><table><tr><th>Epoch</th><th>Training loss</th><th>Native Dice</th><th>Native IoU</th></tr>'+rows+'</table><h2>Final epoch per patient</h2><table><tr><th>Exam</th><th>Dice</th><th>Reference mL</th><th>Prediction mL</th></tr>'+patientrows+'</table><p>Values compare the supplied annotation union (IDs 1, 2, 4), with threshold 0.5 on the original volume grid. These are annotation agreement scores, not diagnostic accuracy.</p><p><a href="summary.json">Summary</a> · <a href="history.json">Full metrics</a> · <a href="protocol.json">Protocol</a> · <a href="provenance.json">Provenance</a></p></html>',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
