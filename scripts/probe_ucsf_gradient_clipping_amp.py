"""Clip unscaled gradients in the predeclared epoch-five diagnostic intervention."""
from pathlib import Path
import json,hashlib,time
import torch,numpy as np
from torch.utils.data import DataLoader
from neurofusion.tumor_segmentation import TumorUNet,segmentation_loss
from neurofusion.ucsf_loader import UCSFSlices
from neurofusion.replay import state_equal
from neurofusion.gradient_control import clip_unscaled_gradients
root=Path(__file__).resolve().parents[1];run=root/'experiments/ucsf-lr-confirm-seed43-baseline';out=root/'experiments/ucsf-gradient-clip-probe-002';out.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=read(run/'summary.json')
intervention=read(root/'configs/ucsf_gradient_clip_amp_protocol.json')
if intervention['max_norm']!=1.0 or intervention['error_if_nonfinite']:raise ValueError('Unexpected intervention')
(out/'intervention-protocol.json').write_text(json.dumps(intervention,indent=2)+'\n',encoding='utf-8')
for name in ('epoch-04.pt','epoch-05.pt'):
    if sha(run/name)!=summary['checkpoints'][name]:raise ValueError('Checkpoint hash mismatch')
cache=root/'experiments/ucsf-specialist-cache-001'
if sha(cache/'manifest.json')!=sha(run/'cache-manifest.json'):raise ValueError('Cache manifest changed')
train=UCSFSlices(cache,'train');manifest=read(cache/'manifest.json')
selected=read(root/'experiments/ucsf-training-diagnostics-001/protocol.json')['training_patients']
probe_indices=[]
for exam in selected:
    entries=[(i,c,z) for i,(c,z,e) in enumerate(train.index) if e==exam]
    for positive in (True,False):
        subset=[i for i,c,z in entries if bool(train.arrays[c][1][z].any())==positive]
        if not subset:raise ValueError('Probe slice group absent')
        probe_indices.append(subset[len(subset)//2])
probe=torch.stack([train[i]['image'] for i in probe_indices]).cuda();probe_target=torch.stack([train[i]['target'] for i in probe_indices]).cuda()
protocol={'purpose':'post hoc gradient clipping intervention; only clipping changes','run':str(run.relative_to(root)),'start_epoch':4,'replay_epoch':5,'fixed_threshold':.5,'probes':[{'exam_id':train[i]['exam_id'],'canonical_z':train[i]['canonical_z'],'foreground_pixels':int(train[i]['target'].sum())} for i in probe_indices],'probe_selection':'four previously hash-selected training patients; median positive and median empty axial slice per patient','evidence_limit':'post hoc intervention from epoch four; not full training or independent validation'}
(out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
checkpoint=torch.load(run/'epoch-04.pt',map_location='cpu',weights_only=False)
expected=torch.load(run/'epoch-05.pt',map_location='cpu',weights_only=False)
torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
model=TumorUNet().cuda();model.load_state_dict(checkpoint['model_state_dict'])
optimizer=torch.optim.Adam(model.parameters(),lr=.001);optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
scaler=torch.amp.GradScaler('cuda');scaler.load_state_dict(checkpoint['scaler_state_dict'])
generator=torch.Generator();generator.set_state(checkpoint['loader_rng'])
loader=DataLoader(train,batch_size=8,shuffle=True,generator=generator,num_workers=0)
torch.set_rng_state(checkpoint['torch_rng']);torch.cuda.set_rng_state_all(checkpoint['cuda_rng'])

def probe_stats():
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):logits=model(probe)
    p=logits.float().sigmoid();pred=p>=.5;y=probe_target.bool()
    return {'max_probability':float(p.max()),'predicted_voxels':int(pred.sum()),'foreground_mean':float(p[y].mean()),'background_mean':float(p[~y].mean()),'tp':int((pred&y).sum()),'fp':int((pred&~y).sum()),'fn':int((~pred&y).sum())}

initial=probe_stats();trace=[];total=0;skipped=0;start=time.time();model.train()
with (out/'trace.jsonl').open('w',encoding='utf-8') as stream:
    for step,b in enumerate(loader,1):
        x,y=b['image'].cuda(),b['target'].cuda();before=torch.nn.utils.parameters_to_vector(model.parameters()).detach().clone()
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.float16):logits=model(x);loss=segmentation_loss(logits,y)
        if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
        with torch.no_grad():
            bce=torch.nn.functional.binary_cross_entropy_with_logits(logits.float(),y).item()
        scaler.scale(loss).backward();scaler.unscale_(optimizer)
        finite=all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
        gradients=torch.cat([p.grad.detach().flatten().double() for p in model.parameters() if p.grad is not None])
        gradnorm=float(gradients.norm()) if finite else None
        clip_before,clip_after=clip_unscaled_gradients(model.parameters(),1.0) if finite else (None,None)
        if finite and clip_after>1.00001:raise RuntimeError('Clipping failed')
        scale_before=scaler.get_scale();scaler.step(optimizer);scaler.update();skipped+=int(not finite)
        delta=(torch.nn.utils.parameters_to_vector(model.parameters()).detach()-before).double()
        row={'step':step,'loss':loss.item(),'bce':bce,'soft_dice_loss':loss.item()-bce,'foreground_pixels':int(y.sum()),'positive_slices':int(y.flatten(1).any(dim=1).sum()),'batch':[{'exam':e,'z':z} for e,z in zip(b['exam_id'],b['canonical_z'].tolist())],'gradient_l2':gradnorm,'post_clip_gradient_l2':clip_after,'clipping_applied':finite and clip_before>1.0,'update_l2':float(delta.norm()),'relative_update_l2':float(delta.norm()/before.double().norm()),'amp_skipped':not finite,'scale_before':scale_before,'scale_after':scaler.get_scale(),'probe':probe_stats()}
        trace.append(row);stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush();total+=loss.item()*len(x)
        if step%50==0:print(f'Replayed {step}/310; probe foreground pixels {row["probe"]["predicted_voxels"]}',flush=True)

control=root/'experiments/ucsf-epoch-replay-001'
control_trace=[json.loads(line) for line in (control/'trace.jsonl').read_text().splitlines()]
checks={'all_310_batches_identical':len(trace)==len(control_trace)==310 and all(a['batch']==b['batch'] for a,b in zip(trace,control_trace)),
        'initial_probe_identical':initial==read(control/'summary.json')['initial_probe'],
        'loader_rng_identical':state_equal(generator.get_state(),expected['loader_rng']),
        'torch_rng_identical':state_equal(torch.get_rng_state(),expected['torch_rng']),
        'cuda_rng_identical':state_equal(torch.cuda.get_rng_state_all(),expected['cuda_rng']),
        'all_post_clip_norms_bounded':all(r['amp_skipped'] or r['post_clip_gradient_l2']<=1.00001 for r in trace)}
if not all(checks.values()):raise RuntimeError('Intervention controls failed')
torch.save({'model_state_dict':model.state_dict(),'optimizer_state_dict':optimizer.state_dict(),'scaler_state_dict':scaler.state_dict(),'epoch':5,'purpose':'diagnostic intervention only'},out/'epoch-05.pt')
result={'controls':checks,'steps':len(trace),'clipped_updates':sum(r['clipping_applied'] for r in trace),'initial_probe':initial,'final_probe':trace[-1]['probe'],'train_loss':total/len(train),'amp_skipped_updates':skipped,'elapsed_seconds':time.time()-start,'model_promoted':False,'weights_changed_in_active_app':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(out/'provenance.json').write_text(json.dumps({'start_checkpoint_sha256':sha(run/'epoch-04.pt'),'control_final_checkpoint_sha256':sha(run/'epoch-05.pt'),'cache_manifest_sha256':sha(cache/'manifest.json'),'script_sha256':sha(Path(__file__)),'gradient_control_sha256':sha(root/'src/neurofusion/gradient_control.py'),'final_checkpoint_sha256':sha(out/'epoch-05.pt'),'trace_sha256':sha(out/'trace.jsonl')},indent=2),encoding='utf-8')
(out/'intervention-script.py').write_bytes(Path(__file__).read_bytes())
(out/'gradient_control.py').write_bytes((root/'src/neurofusion/gradient_control.py').read_bytes())
print(json.dumps(result,indent=2),flush=True)
