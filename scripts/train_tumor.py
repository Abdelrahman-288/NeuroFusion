"""Five-epoch image-classification baseline on frozen BRISC development partitions."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse
import json
from pathlib import Path
import time
import shutil
import numpy as np
import torch
from neurofusion.tumor import TumorCNN,CLASSES,load_partition,classification_metrics
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.augmentation import augment, POLICY, augment_contrast, CONTRAST_POLICY


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['root','splits','output']: p.add_argument('--'+name,type=Path,required=True)
    policy_args=p.add_mutually_exclusive_group()
    policy_args.add_argument('--intensity-augmentation',action='store_true')
    policy_args.add_argument('--contrast-augmentation',action='store_true')
    p.add_argument('--seed',type=int,default=42)
    args=p.parse_args()
    if args.output.exists(): p.error('Fresh output required')
    if not torch.cuda.is_available(): p.error('CUDA required')
    args.output.mkdir(parents=True)
    config={'architecture':'compact-2d-cnn-16-32-64-4x4-v1','classes':list(CLASSES),'seed':args.seed,
        'epochs':5,'batch_size':32,'learning_rate':.001,'optimizer':'Adam','loss':'cross entropy',
        'preprocessing':'PIL grayscale, bilinear 128x128 resize, divide by 255; no augmentation',
        'pretrained':False,'split_sha256':digest(args.splits),'split_path':str(args.splits.resolve()),
        'root':str(args.root.resolve()),'torch':str(torch.__version__),'test_evaluated':False,
        'selection':'best validation macro F1; final epoch also reported',
        'limitations':'Image-group split; patient independence unverified; no_tumor is not healthy; softmax scores uncalibrated'}
    use_augmentation=args.intensity_augmentation or args.contrast_augmentation
    augmentation_policy=dict(CONTRAST_POLICY if args.contrast_augmentation else POLICY,seed=args.seed+1000)
    config['augmentation']=augmentation_policy if use_augmentation else None
    if use_augmentation:
        config['preprocessing']='PIL grayscale, bilinear 128x128, divide by 255; training-only intensity augmentation'
        config['comparison']='Final epoch 5 against baseline final epoch 5; no early selection for the comparison'
    save_json(args.output/'config.json',config)
    source=args.output/'source';source.mkdir()
    for path in [Path(__file__),Path(__file__).resolve().parents[1]/'src/neurofusion/augmentation.py',Path(__file__).resolve().parents[1]/'src/neurofusion/tumor.py']:
        shutil.copy2(path,source/path.name)
    save_json(args.output/'source-hashes.json',{p.name:digest(p) for p in source.iterdir()})
    began=time.perf_counter()
    print('Verifying and preparing training images',flush=True)
    x,y,train=load_partition(args.root,args.splits,'train')
    print('Verifying and preparing validation images',flush=True)
    vx,vy,validation=load_partition(args.root,args.splits,'validation')
    save_json(args.output/'coverage.json',{'train_paths':[r['path'] for r in train],'validation_paths':[r['path'] for r in validation],
        'test_loaded':False,'all_active_source_hashes_verified':True,'group_overlap':False})
    torch.manual_seed(args.seed); torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True); torch.backends.cudnn.benchmark=False
    model=TumorCNN().cuda(); optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    scaler=torch.amp.GradScaler('cuda'); rng=np.random.default_rng(args.seed)
    augmentation_rng=np.random.default_rng(augmentation_policy['seed'])
    best=-1; history=[]; updates=0
    for epoch in range(1,6):
        model.train(); losses=[]; order=rng.permutation(len(y)); visited=[]
        for start in range(0,len(y),32):
            indices=order[start:start+32]; visited.extend(indices.tolist())
            if use_augmentation:
                transform=augment_contrast if args.contrast_augmentation else augment
                tx=torch.from_numpy(transform(x[indices].astype(np.float32)/255,augmentation_rng)).cuda()
            else:
                tx=torch.from_numpy(x[indices]).cuda().float()/255
            ty=torch.from_numpy(y[indices]).cuda()
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast('cuda',dtype=torch.float16):
                loss=torch.nn.functional.cross_entropy(model(tx),ty)
            if not torch.isfinite(loss): raise RuntimeError('Nonfinite training loss')
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            losses.append(float(loss.detach().cpu())*len(indices)); updates+=1
        if sorted(visited)!=list(range(len(y))): raise RuntimeError('Training coverage failure')
        model.eval(); probabilities=[]
        with torch.inference_mode():
            for start in range(0,len(vy),32):
                tensor=torch.from_numpy(vx[start:start+32]).cuda().float()/255
                probabilities.append(model(tensor).float().softmax(1).cpu().numpy())
        probs=np.concatenate(probabilities)
        score=classification_metrics(vy,probs)
        record={'epoch':epoch,'updates':updates,'train_loss':sum(losses)/len(y),'train_images_seen':len(visited),**score}
        history.append(record)
        state={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'scaler':scaler.state_dict(),'config':config,
               'epoch':epoch,'history':history,'numpy_rng':rng.bit_generator.state,'torch_rng':torch.get_rng_state(),
               'cuda_rng':torch.cuda.get_rng_state_all()}
        state['augmentation_rng']=augmentation_rng.bit_generator.state
        torch.save(state,args.output/'last.pt')
        if score['macro_f1']>best:
            best=score['macro_f1']; torch.save(state,args.output/'best.pt')
        save_json(args.output/'history.json',history)
        save_json(args.output/'validation-predictions.json',[{'path':r['path'],'group_id':r['group_id'],'reference':r['label'],
            'predicted':CLASSES[int(prob.argmax())],'probabilities':prob.tolist()} for r,prob in zip(validation,probs)])
        rows=''.join(f'<tr><td>{h["epoch"]}</td><td>{h["train_loss"]:.4f}</td><td>{h["accuracy"]:.3f}</td><td>{h["macro_f1"]:.3f}</td></tr>' for h in history)
        (args.output/'progress.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="20"><title>BRISC training</title><style>body{font:18px system-ui;max-width:950px;margin:40px auto}td,th{padding:12px}progress{width:100%;height:25px}</style><h1>NeuroFusion tumor classifier</h1>'+f'<p>Epoch {epoch}/5 · {len(y)} training images · {len(vy)} validation images</p><progress value="{epoch}" max="5"></progress><table><tr><th>Epoch</th><th>Training loss</th><th>Validation accuracy</th><th>Macro F1</th></tr>'+rows+'</table><p>Research image-classification baseline. Patient independence unverified; test images unused; no_tumor does not mean healthy.</p>',encoding='utf-8')
        print(json.dumps({k:v for k,v in record.items() if k not in ['confusion_matrix','per_class']}),flush=True)
    summary={'completed':True,'train_images':len(y),'validation_images':len(vy),'test_evaluated':False,'epochs':5,
        'updates':updates,'parameters':sum(p.numel() for p in model.parameters()),'elapsed_seconds':time.perf_counter()-began,
        'final_validation':history[-1],'best_epoch':max(history,key=lambda h:h['macro_f1'])['epoch'],
        'best_macro_f1':best,'last_checkpoint_sha256':digest(args.output/'last.pt'),
        'best_checkpoint_sha256':digest(args.output/'best.pt'),'predictions_checkpoint':'last.pt'}
    save_json(args.output/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
