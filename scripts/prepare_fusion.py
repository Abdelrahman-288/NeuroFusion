"""Check development DWI/ADC geometry, render paired slices and exercise two-channel GPU training."""
import argparse
import json
from pathlib import Path
import nibabel as nib
import numpy as np
import torch
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.fusion import load_fusion_study
from neurofusion.segmentation import CompactUNet,sample_patch,segmentation_loss
from preview_studies import png


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['manifest','splits','cache','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    store=StudyStore(args.manifest,args.splits,args.cache)
    args.output.mkdir(parents=True)
    rows=[]; cards=[]; smoke=None
    for partition in ['train','validation']:
        for study in store.studies(partition):
            subject=study['subject_id']
            try:
                image,mask,meta=load_fusion_study(store,study)
                row={'subject':subject,'partition':partition,'grid_passed':True,
                     'shape':list(image.shape),'adc_sha256':meta['adc_sha256'],
                     'adc_statistics':meta['adc_statistics']}
                if len(cards)<4 and partition=='train':
                    z=int(np.argmax(mask.sum(axis=(0,1))))
                    panels=[]
                    for values in image:
                        low,high=np.percentile(values[values!=0],[1,99])
                        gray=(np.clip((np.rot90(values[:,:,z])-low)/max(high-low,1e-8),0,1)*255).astype(np.uint8)
                        panels.append(np.repeat(gray[:,:,None],3,axis=2))
                    overlay=panels[0].copy()
                    plane=np.rot90(mask[:,:,z]>0)
                    overlay[plane]=(.45*overlay[plane]+.55*np.array([255,60,60])).astype(np.uint8)
                    name=f'{subject}.png'
                    png(args.output/name,np.concatenate(panels+[overlay],axis=1))
                    cards.append(f'<h2>{subject} · slice {z}</h2><p>DWI | ADC | DWI with reference mask</p><img src="{name}" style="width:100%;image-rendering:pixelated">')
                if smoke is None and partition=='train':
                    if not torch.cuda.is_available():
                        raise RuntimeError('CUDA required for this readiness check')
                    torch.manual_seed(42)
                    torch.set_num_threads(2)
                    model=CompactUNet(in_channels=2).cuda()
                    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
                    patch,label=sample_patch(image,mask,np.random.default_rng(42))
                    tx=torch.from_numpy(patch)[None].cuda()
                    ty=torch.from_numpy(label.astype(np.float32))[None,None].cuda()
                    losses=[]
                    for _ in range(5):
                        optimizer.zero_grad(set_to_none=True)
                        loss=segmentation_loss(model(tx),ty)
                        if not torch.isfinite(loss):
                            raise RuntimeError('Nonfinite fusion loss')
                        loss.backward(); optimizer.step()
                        losses.append(float(loss.detach().cpu()))
                    smoke={'subject':subject,'steps':5,'losses':losses,'parameters':sum(p.numel() for p in model.parameters()),
                           'input_shape':list(tx.shape),'device':torch.cuda.get_device_name(),
                           'purpose':'Pipeline smoke check only; not a trained or validated fusion model'}
                    del model,optimizer,tx,ty
            except (ValueError,KeyError,OSError) as error:
                row={'subject':subject,'partition':partition,'grid_passed':False,'error':str(error)}
            rows.append(row)
            if len(rows)%25==0:
                print(f'Checked {len(rows)} development pairs',flush=True)
    summary={'studies':len(rows),'passed':sum(r['grid_passed'] for r in rows),'failed':sum(not r['grid_passed'] for r in rows),
             'holdout_loaded':False,'channels':['dwi','adc'],'gpu_smoke':smoke,
             'manifest_sha256':digest(args.manifest),'splits_sha256':digest(args.splits),'cases':rows,
             'limitations':'Equal physical grids do not prove anatomical registration. Only selected paired slices reviewed. No fusion performance claim.'}
    save_json(args.output/'summary.json',summary)
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>DWI + ADC readiness</title><style>body{font:17px system-ui;max-width:1050px;margin:30px auto;padding:20px}</style><h1>DWI + ADC fusion readiness</h1>'+f'<p>{summary["passed"]}/{summary["studies"]} development pairs passed physical-grid and intensity checks. Holdout not loaded.</p><p>Paired images below are selected training examples. Matching geometry is not proof of anatomical registration. GPU smoke check is not model validation.</p>'+''.join(cards),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'},indent=2))


if __name__=='__main__':
    main()
