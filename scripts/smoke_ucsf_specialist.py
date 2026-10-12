"""Two disposable optimizer steps on training slices; saves no trained checkpoint."""
import argparse
import json
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from neurofusion.ucsf_loader import UCSFSlices
from neurofusion.tumor_segmentation import TumorUNet,segmentation_loss

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not torch.cuda.is_available():raise RuntimeError('CUDA required for this smoke test')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(42)
    train=UCSFSlices(a.cache,'train');val=UCSFSlices(a.cache,'development_validation')
    model=TumorUNet().cuda();optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    scaler=torch.amp.GradScaler('cuda');torch.cuda.reset_peak_memory_stats();steps=[]
    loader=DataLoader(train,batch_size=8,shuffle=True,generator=torch.Generator().manual_seed(42),num_workers=0)
    for step,b in enumerate(loader):
        x,y=b['image'].cuda(),b['target'].cuda();before=model.head.weight.detach().clone();optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.float16):logits=model(x);loss=segmentation_loss(logits,y)
        if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
        scaler.scale(loss).backward();scaler.unscale_(optimizer)
        if not all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None):raise RuntimeError('Nonfinite gradients')
        scaler.step(optimizer);scaler.update();torch.cuda.synchronize()
        changed=not torch.equal(before,model.head.weight)
        if not changed:raise RuntimeError('Optimizer did not update parameters')
        steps.append({'loss':loss.item(),'shape':list(logits.shape),'foreground_pixels':int(y.sum()),'parameters_updated':changed,'exam_ids':b['exam_id']})
        if step==1:break
    result={'purpose':'Disposable engineering GPU smoke test, not performance evaluation','device':torch.cuda.get_device_name(),
            'train_slices':len(train),'development_validation_slices':len(val),'steps':steps,
            'peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,
            'parameters':sum(p.numel() for p in model.parameters()),'checkpoint_saved':False,'validation_inference_performed':False,'full_training_started':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
