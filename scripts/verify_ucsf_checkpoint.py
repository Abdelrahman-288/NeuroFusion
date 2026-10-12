"""Reload a locally generated UCSF checkpoint and reproduce native predictions."""
import argparse,json,hashlib
from pathlib import Path
import torch,numpy as np,nibabel as nib
from neurofusion.tumor_segmentation import TumorUNet
from neurofusion.ucsf_validation import score_native


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];out=(root/args.run).resolve()
    if not out.is_relative_to(root/'experiments'):raise ValueError('Expected local experiment')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    summary=read(out/'summary.json');manifest=read(out/'cache-manifest.json');parts=read(out/'partitions.json');protocol=read(out/'protocol.json')
    for name,checksum in summary['checkpoints'].items():
        path=out/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:raise ValueError('Checkpoint hash mismatch')
        checkpoint=torch.load(path,map_location='cpu',weights_only=False)
        if any(g['lr']!=protocol['training_plan']['learning_rate'] for g in checkpoint['optimizer_state_dict']['param_groups']):raise ValueError('Actual optimizer learning rate differs')
    checkpoint=torch.load(out/f"epoch-{summary['completed_epochs']:02d}.pt",map_location='cpu',weights_only=False)
    model=TumorUNet().cuda();model.load_state_dict(checkpoint['model_state_dict']);model.eval();verified=[]
    with torch.inference_mode():
        for case in manifest['cases']:
            if case['role']!='development_validation':continue
            directory=root/'experiments/ucsf-specialist-cache-001'/case['directory'];x=np.load(directory/'images.npy');prob=[]
            if hashlib.sha256((directory/'images.npy').read_bytes()).hexdigest()!=case['sha256']['images.npy']:raise ValueError('Input cache changed')
            for z in range(0,len(x),8):
                with torch.autocast('cuda',dtype=torch.float16):logits=model(torch.from_numpy(x[z:z+8].astype(np.float32)/255).cuda())
                prob.append(logits.float().sigmoid().cpu().numpy()[:,0])
            record=next(r for r in parts['records'] if r['exam_id']==case['exam_id'])
            metrics,prediction=score_native(np.concatenate(prob),read(directory/'geometry.json'),nib.load(root/'data/raw/ucsf-pdgm-v5'/record['mask']['path']))
            if metrics!=next(r for r in summary['final_epoch']['cases'] if r['exam_id']==case['exam_id'])['metrics']:raise ValueError('Metrics differ on reload')
            if not np.array_equal(prediction.get_fdata(),nib.load(out/(case['exam_id']+'-prediction.nii.gz')).get_fdata()):raise ValueError('Saved masks differ')
            verified.append(case['exam_id'])
    result={'checkpoint_hashes_and_optimizer_learning_rates_verified':len(summary['checkpoints']),'reloaded_final_masks_and_metrics_exact':verified}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(result)

if __name__=='__main__':main()
