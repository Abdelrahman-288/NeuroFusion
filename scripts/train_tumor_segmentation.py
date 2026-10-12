"""Train and evaluate first BRISC 2D tumor segmentation baseline."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.tumor_segmentation import load_segmentation,TumorUNet,segmentation_loss,native_probability,mask_metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['root','splits','output']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=5)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    if not 1<=args.epochs<=100: parser.error('Require 1-100 epochs')
    if args.output.exists(): parser.error('Fresh output required')
    if not torch.cuda.is_available(): parser.error('CUDA required')
    args.output.mkdir(parents=True)
    config={'architecture':'2d-unet-8-16-32-v1','seed':args.seed,'epochs':args.epochs,'batch_size':16,'lr':.001,
        'mask_policy':'uint8 values <=10 background, >=246 foreground; threshold 128; reject gap values',
        'preprocessing':'grayscale bilinear 128x128 image /255; nearest-neighbor binary mask',
        'evaluation':'restore probabilities bilinearly to original dimensions; threshold 0.5',
        'loss':'BCE + per-image soft Dice','root':str(args.root.resolve()),'splits':str(args.splits.resolve()),
        'split_sha256':digest(args.splits),'publisher_manifest_sha256':digest(args.root/'manifest.json'),
        'torch':str(torch.__version__),'test_loaded':False,'no_tumor_used':False,
        'limitations':'Image groups not patient IDs; positive-only segmentation; no physical volume or clinical claims'}
    checkpoint=torch.load(args.resume,weights_only=True,map_location='cpu') if args.resume else None
    if checkpoint:
        old={k:v for k,v in checkpoint['config'].items() if k!='epochs'}
        new={k:v for k,v in config.items() if k!='epochs'}
        if old!=new or checkpoint['epoch']>=args.epochs: raise ValueError('Resume config/data mismatch or invalid target epoch')
    save_json(args.output/'config.json',config)
    save_json(args.output/'run-request.json',{'epochs':args.epochs,'resume':str(args.resume) if args.resume else None,'resume_sha256':digest(args.resume) if args.resume else None})
    clock=time.perf_counter()
    print('Loading and validating training image/mask pairs',flush=True)
    x,y,_,train=load_segmentation(args.root,args.splits,'train',keep_native=False)
    print('Loading and validating validation image/mask pairs',flush=True)
    vx,vy,native,validation=load_segmentation(args.root,args.splits,'validation')
    save_json(args.output/'data-coverage.json',{'train':train,'validation':validation,'test_loaded':False})
    print(json.dumps({'train_pairs':len(train),'validation_pairs':len(validation)}),flush=True)
    torch.manual_seed(args.seed); torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False
    model=TumorUNet().cuda(); optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    scaler=torch.amp.GradScaler('cuda'); rng=np.random.default_rng(args.seed)
    history=[]; best=-1; updates=0
    start_epoch=0
    if checkpoint:
        model.load_state_dict(checkpoint['model']);optimizer.load_state_dict(checkpoint['optimizer'])
        scaler.load_state_dict(checkpoint['scaler']);rng.bit_generator.state=checkpoint['numpy_rng']
        torch.set_rng_state(checkpoint['torch_rng']);torch.cuda.set_rng_state_all(checkpoint['cuda_rng'])
        history=checkpoint['history'];start_epoch=checkpoint['epoch']
        updates=history[-1]['updates'];best=max(h['mean_dice'] for h in history)
        torch.save(checkpoint,args.output/'resume-source.pt')
    for epoch in range(start_epoch+1,args.epochs+1):
        model.train(); losses=[]; order=rng.permutation(len(train)); visited=[]
        for start in range(0,len(train),16):
            indices=order[start:start+16]; visited.extend(indices.tolist())
            tx=torch.from_numpy(x[indices]).cuda().float()/255
            ty=torch.from_numpy(y[indices]).cuda().float()
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.float16): loss=segmentation_loss(model(tx),ty)
            if not torch.isfinite(loss): raise RuntimeError('Nonfinite loss')
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            losses.append(float(loss.detach().cpu())*len(indices)); updates+=1
        if sorted(visited)!=list(range(len(train))): raise RuntimeError('Training coverage failed')
        model.eval(); cases=[]
        if epoch==args.epochs: (args.output/'predictions').mkdir()
        with torch.inference_mode():
            for start in range(0,len(validation),16):
                tensor=torch.from_numpy(vx[start:start+16]).cuda().float()/255
                probs=model(tensor).float().sigmoid()[:,0].cpu().numpy()
                for offset,prob in enumerate(probs):
                    i=start+offset; row=validation[i]
                    restored=native_probability(prob,native[i].shape)
                    score=mask_metrics(restored,native[i])
                    case={'path':row['path'],'group_id':row['group_id'],'label':row['label'],**score}
                    if epoch==args.epochs:
                        name=f'{i:04d}.npz'
                        np.savez_compressed(args.output/'predictions'/name,probability=prob)
                        case.update(prediction=name,prediction_sha256=digest(args.output/'predictions'/name))
                    cases.append(case)
        by_class={label:float(np.mean([c['dice'] for c in cases if c['label']==label])) for label in sorted({c['label'] for c in cases})}
        result={'epoch':epoch,'updates':updates,'train_seen':len(visited),'validation_seen':len(cases),
            'training_loss':sum(losses)/len(train),'mean_dice':float(np.mean([c['dice'] for c in cases])),
            'median_dice':float(np.median([c['dice'] for c in cases])),'mean_iou':float(np.mean([c['iou'] for c in cases])),
            'per_class_dice':by_class}
        history.append(result)
        state={'epoch':epoch,'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scaler':scaler.state_dict(),
               'config':config,'history':history,'numpy_rng':rng.bit_generator.state,'torch_rng':torch.get_rng_state(),
               'cuda_rng':torch.cuda.get_rng_state_all()}
        torch.save(state,args.output/'last.pt')
        if result['mean_dice']>best:
            best=result['mean_dice']; torch.save(state,args.output/'best.pt')
        save_json(args.output/'history.json',history)
        if epoch==args.epochs: save_json(args.output/'validation.json',cases)
        rows=''.join(f'<tr><td>{h["epoch"]}</td><td>{h["training_loss"]:.4f}</td><td>{h["mean_dice"]:.4f}</td><td>{h["mean_iou"]:.4f}</td></tr>' for h in history)
        (args.output/'progress.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="20"><title>Tumor segmentation training</title><style>body{font:18px system-ui;max-width:950px;margin:35px auto}td,th{padding:12px}progress{width:100%}</style><h1>BRISC tumor segmentation</h1>'+f'<p>Epoch {epoch}/{args.epochs} · {len(train)} training pairs · {len(validation)} validation pairs</p><progress value="{epoch}" max="{args.epochs}"></progress><table><tr><th>Epoch</th><th>Loss</th><th>Native-size Dice</th><th>Native-size IoU</th></tr>'+rows+'</table><p>2D research segmentation on supplied tumor-positive masks; test images unused; patient independence unverified.</p>',encoding='utf-8')
        print(json.dumps(result),flush=True)
    summary={'completed':True,'train_pairs':len(train),'validation_pairs':len(validation),'test_loaded':False,'epochs':args.epochs,'resumed_from_epoch':start_epoch,
        'updates':updates,'parameters':sum(p.numel() for p in model.parameters()),'elapsed_seconds':time.perf_counter()-clock,
        'final_validation':history[-1],'best_epoch':max(history,key=lambda h:h['mean_dice'])['epoch'],
        'best_mean_dice':best,'last_sha256':digest(args.output/'last.pt'),'best_sha256':digest(args.output/'best.pt') if (args.output/'best.pt').exists() else None,
        'predictions_checkpoint':'last.pt; 128x128 float32 probabilities restored to native dimensions for scoring'}
    save_json(args.output/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
