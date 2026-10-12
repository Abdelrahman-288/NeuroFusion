"""Full frozen training cohort, bounded memory, full-volume validation only."""
import argparse
import ctypes
import hashlib
import html
import json
import os
from pathlib import Path
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import numpy as np
import torch
from neurofusion.cohort import StudyStore,digest,epoch_order
from neurofusion.fusion import load_fusion_study
from neurofusion.data import save_json
from neurofusion.preprocessing import restore_prediction
from neurofusion.segmentation import CompactUNet,segmentation_loss,sample_patch,predict_volume,metrics,component_coordinates


def peak_rss():
    if os.name!='nt':
        return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in
            ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    result=Counters()
    result.cb=ctypes.sizeof(result)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1),ctypes.byref(result),result.cb):
        return result.PeakWorkingSetSize
    return None


def progress(output,config,history,validations,status):
    input_label=' + '.join(config.get('inputs',['dwi'])).upper()
    # Show 25-step mean losses for a readable plot, preserving raw JSON history.
    points_y=[float(np.mean([r['loss'] for r in history[i:i+25]])) for i in range(0,len(history),25)]
    high=max(points_y,default=1)
    points=' '.join(f'{30+i*730/max(1,len(points_y)-1):.1f},{240-v/max(high,1e-8)*200:.1f}' for i,v in enumerate(points_y))
    def volume_text(value):
        return f'{value:.2f}' if value is not None else 'Unknown units'
    rows=''.join(f"<tr><td>{v['epoch']}</td><td>{v['mean_dice']:.4f}</td><td>{v['median_dice']:.4f}</td><td>{volume_text(v['mean_absolute_volume_error_ml'])}</td><td>{len(v['cases'])}</td></tr>" for v in validations)
    content=f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="20"><title>NeuroFusion cohort training</title>
<style>body{{font:17px system-ui;max-width:1050px;margin:35px auto;padding:20px;color:#19384c;background:#f7fafc}}svg{{width:100%;background:white}}td,th{{padding:10px;text-align:left}}.note{{background:#fff1cd;padding:16px}}</style></head><body>
<h1>NeuroFusion · Full-cohort {input_label} baseline</h1><p>{html.escape(status)}</p><p>{len(config['train_subjects'])} training studies · {len(config['validation_subjects'])} validation studies · {len(history)} optimizer steps</p>
<p class="note">Research development run. The holdout is not loaded or evaluated. Validation is used for development and checkpoint selection; results are not clinical accuracy.</p>
<h2>Training loss (25-step averages)</h2><svg viewBox="0 0 800 265" role="img" aria-label="Mean training loss"><polyline points="{points}" fill="none" stroke="#008080" stroke-width="2"/></svg>
<h2>All-study full-volume validation</h2><table><tr><th>Epoch</th><th>Mean Dice</th><th>Median Dice</th><th>Mean absolute volume error, mL</th><th>Studies</th></tr>{rows}</table>
<p>Fixed threshold 0.5. Native voxel spacing, {input_label}. <a href="validation.json">Per-case metrics</a> · <a href="history.json">Training history</a> · <a href="summary.json">Summary after completion</a></p></body></html>'''
    temporary=output/'progress.tmp'
    temporary.write_text(content,encoding='utf-8')
    temporary.replace(output/'progress.html')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','splits','cache','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=5)
    parser.add_argument('--patches-per-study',type=int,default=8)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--sampling',choices=['voxel','component'],default='voxel')
    parser.add_argument('--inputs',choices=['dwi','dwi-adc'],default='dwi')
    args=parser.parse_args()
    if args.output.exists() or not 1<=args.epochs<=100 or not 1<=args.patches_per_study<=64:
        parser.error('Fresh output, 1-100 total epochs and 1-64 patches per study required')
    if not torch.cuda.is_available():
        parser.error('CUDA required')
    store=StudyStore(args.manifest,args.splits,args.cache)
    training,validation=store.studies('train'),store.studies('validation')
    config={'architecture':'compact-unet-8-16-32-strideconv-nearest-v1','torch':str(torch.__version__),
        'seed':42,'lr':.001,'patch':32,'patches_per_study':args.patches_per_study,'threshold':.5,
        'loss':'BCE + soft Dice','augmentation':'none; initial full-cohort baseline',
        'preprocessing':store.version,'native_spacing':True,'validation_overlap':.5,
        'manifest_sha256':digest(args.manifest),'splits_sha256':digest(args.splits),
        'train_subjects':[s['subject_id'] for s in training],
        'validation_subjects':[s['subject_id'] for s in validation],
        'sampling':'one seeded shuffled pass over every study per epoch; 50% lesion-centered training patches',
        'holdout_evaluated':False,'deterministic_algorithms':True}
    checkpoint=torch.load(args.resume,weights_only=True,map_location='cpu') if args.resume else None
    if args.sampling=='component':
        config['sampling']='one seeded shuffled pass over every study per epoch; 50% foreground patches; uniform 26-connected component then uniform voxel within component'
    if args.inputs=='dwi-adc':
        config.update(architecture='compact-unet-8-16-32-strideconv-nearest-2channel-v1',
                      inputs=['dwi','adc'],preprocessing='dwi-adc-native-ras-independent-zscore-v1')
    def load_study(study):
        if args.inputs=='dwi-adc':
            x,y,meta=load_fusion_study(store,study)
            store.max_study_bytes=max(store.max_study_bytes,x.nbytes+y.nbytes)
            return x,y,meta
        return store.load(study)
    if checkpoint and (checkpoint['config']!=config or checkpoint['epoch']>=args.epochs):
        parser.error('Resume config/data must match and target epochs must exceed checkpoint epoch')
    args.output.mkdir(parents=True)
    save_json(args.output/'config.json',config)
    save_json(args.output/'run-request.json',{'epochs':args.epochs,'resume':str(args.resume) if args.resume else None})
    progress(args.output,config,[],[],'Preparing disk cache')
    began=time.perf_counter()
    for i,study in enumerate(training+validation):
        store.prepare(study)
        if (i+1)%20==0:
            print(json.dumps({'prepared':i+1,'total':len(training)+len(validation)}),flush=True)
    preparation_seconds=time.perf_counter()-began
    torch.manual_seed(42)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.benchmark=False
    rng=np.random.default_rng(42)
    model=CompactUNet(in_channels=2 if args.inputs=='dwi-adc' else 1).cuda()
    optimizer=torch.optim.Adam(model.parameters(),lr=config['lr'])
    scaler=torch.amp.GradScaler('cuda')
    history,validations=[],[]
    start_epoch=0
    best=-1.
    if checkpoint:
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        scaler.load_state_dict(checkpoint['scaler'])
        rng.bit_generator.state=checkpoint['numpy_rng']
        torch.set_rng_state(checkpoint['torch_rng'])
        torch.cuda.set_rng_state_all(checkpoint['cuda_rng'])
        history,validations=checkpoint['history'],checkpoint['validations']
        start_epoch,best=checkpoint['epoch'],checkpoint['best_dice']
    torch.cuda.reset_peak_memory_stats()
    clock=time.perf_counter()
    def save_checkpoint(epoch,name):
        temp=args.output/(name+'.tmp')
        torch.save({'epoch':epoch,'config':config,'model':model.state_dict(),'optimizer':optimizer.state_dict(),
            'scaler':scaler.state_dict(),'numpy_rng':rng.bit_generator.state,'torch_rng':torch.get_rng_state(),
            'cuda_rng':torch.cuda.get_rng_state_all(),'history':history,'validations':validations,'best_dice':best},temp)
        temp.replace(args.output/name)
    for epoch in range(start_epoch+1,args.epochs+1):
        for index in epoch_order(len(training),42,epoch):
            study=training[index]
            x,y,_=load_study(study)
            model.train()
            components=component_coordinates(y) if args.sampling=='component' else None
            for _ in range(args.patches_per_study):
                patch,label=sample_patch(x,y,rng,size=config['patch'],components=components)
                tx=torch.from_numpy(patch)[None].cuda() if patch.ndim==4 else torch.from_numpy(patch)[None,None].cuda()
                ty=torch.from_numpy(label.astype(np.float32))[None,None].cuda()
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):
                    loss=segmentation_loss(model(tx),ty)
                if not torch.isfinite(loss):
                    raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                history.append({'step':len(history)+1,'epoch':epoch,'subject':study['subject_id'],'loss':float(loss.detach().cpu())})
                if len(history)%200==0:
                    save_json(args.output/'history.json',history)
                    progress(args.output,config,history,validations,f'Training epoch {epoch}/{args.epochs}')
                    print(json.dumps(history[-1]),flush=True)
            del x,y
        cases=[]
        for i,study in enumerate(validation):
            x,y,meta=load_study(study)
            probability=predict_volume(model,x,'cuda',patch=config['patch'],overlap=config['validation_overlap'])
            score=metrics(probability,y)
            scale={'mm':1.,'meter':1000.,'micron':.001}.get(meta['xyzt_units'][0])
            voxel_ml=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))*scale**3/1000 if scale else None
            score['absolute_volume_error_ml']=abs(score['predicted_voxels']-score['reference_voxels'])*voxel_ml if voxel_ml else None
            cases.append({'subject':study['subject_id'],**score})
            if epoch==args.epochs:
                restore_prediction(probability,meta,args.output/'predictions'/f"{study['subject_id']}-probability.nii.gz")
            del x,y,probability
            if (i+1)%10==0:
                print(json.dumps({'epoch':epoch,'validation_completed':i+1,'total':len(validation)}),flush=True)
                progress(args.output,config,history,validations,f'Validating epoch {epoch}: {i+1}/{len(validation)} volumes')
        volumes=[c['absolute_volume_error_ml'] for c in cases if c['absolute_volume_error_ml'] is not None]
        result={'epoch':epoch,'step':len(history),'mean_dice':float(np.mean([c['dice'] for c in cases])),
            'median_dice':float(np.median([c['dice'] for c in cases])),
            'mean_absolute_volume_error_ml':float(np.mean(volumes)) if volumes else None,'cases':cases}
        validations.append(result)
        if result['mean_dice']>best:
            best=result['mean_dice']
            save_checkpoint(epoch,'best.pt')
        save_checkpoint(epoch,'last.pt')
        save_json(args.output/'validation.json',validations)
        progress(args.output,config,history,validations,f'Epoch {epoch}/{args.epochs} complete')
        print(json.dumps({k:v for k,v in result.items() if k!='cases'}),flush=True)
    torch.cuda.synchronize()
    save_json(args.output/'history.json',history)
    summary={'completed':True,'total_epochs':args.epochs,'resumed_from_epoch':start_epoch,'steps':len(history),
        'train_studies':len(training),'validation_studies':len(validation),'holdout_evaluated':False,
        'final_validation':validations[-1],'best_mean_validation_dice':best,
        'predictions_checkpoint':'last.pt; predictions are from final epoch, not necessarily best.pt',
        'elapsed_training_validation_seconds':time.perf_counter()-clock,'preparation_seconds':preparation_seconds,
        'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_process_working_set_bytes':peak_rss(),
        'largest_loaded_image_and_mask_bytes':store.max_study_bytes,
        'limitations':'Short native-spacing experiment; validation used for selection; lesion metrics require separate evaluation; no external-site evidence'}
    save_json(args.output/'summary.json',summary)
    progress(args.output,config,history,validations,'Completed')
    print(json.dumps({k:v for k,v in summary.items() if k!='final_validation'},indent=2),flush=True)


if __name__=='__main__':
    main()
