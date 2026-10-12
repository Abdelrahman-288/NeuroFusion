"""Deterministic best/median/worst validation slice examples from a final checkpoint."""
import argparse
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore
from preview_studies import png


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','manifest','splits','cache']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    output=args.run/'prediction-preview'
    if output.exists():
        parser.error('Preview already exists')
    summary=json.loads((args.run/'summary.json').read_text())
    ranked=sorted(summary['final_validation']['cases'],key=lambda c:(c['dice'],c['subject']))
    chosen=[('Lowest Dice',ranked[0]),('Middle-ranked Dice',ranked[len(ranked)//2]),('Highest Dice',ranked[-1])]
    store=StudyStore(args.manifest,args.splits,args.cache)
    studies={s['subject_id']:s for s in store.studies('validation')}
    output.mkdir()
    cards=[]
    for rank,case in chosen:
        subject=case['subject']
        image,reference,meta=store.load(studies[subject])
        pred_image=nib.as_closest_canonical(nib.load(args.run/'predictions'/f'{subject}-probability.nii.gz'))
        probability=pred_image.get_fdata(dtype=np.float32)
        if probability.shape!=image.shape or not np.allclose(pred_image.affine,meta['canonical_affine'],atol=1e-4,rtol=0):
            raise ValueError('Prediction/preprocessing grid mismatch')
        prediction=probability>=.5
        slices=sorted({int(np.argmax(reference.sum(axis=(0,1)))),int(np.argmax(prediction.sum(axis=(0,1))))})
        low,high=np.percentile(image[image!=0],[1,99])
        cards.append(f'<section><h2>{rank}: {html.escape(subject)} · whole-volume Dice {case["dice"]:.3f}</h2>')
        for z in slices:
            gray=(np.clip((np.rot90(image[:,:,z])-low)/max(high-low,1e-8),0,1)*255).astype(np.uint8)
            plain=np.repeat(gray[:,:,None],3,axis=2)
            panels=[plain]
            for mask in (reference>0,prediction):
                overlay=plain.copy()
                plane=np.rot90(mask[:,:,z])
                overlay[plane]=(.45*overlay[plane]+.55*np.array([255,60,60])).astype(np.uint8)
                panels.append(overlay)
            name=f'{subject}-z{z}.png'
            png(output/name,np.concatenate(panels,axis=1))
            cards.append(f'<p>Slice {z}: DWI | supplied reference | final-model prediction</p><img src="{name}" alt="DWI reference and prediction" style="width:100%;image-rendering:pixelated">')
        cards.append('</section>')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>NeuroFusion cohort examples</title><style>body{font:17px system-ui;max-width:1050px;margin:40px auto;padding:20px;color:#173348}section{border-top:1px solid #bbb;margin-top:30px}</style><h1>Final-epoch validation examples</h1><p>Lowest, middle-ranked and highest Dice among all validation studies. Slices are chosen by maximum reference/predicted area, not a full-volume review. These are development results, not clinical predictions. Display aspect is voxel-based.</p>'+''.join(cards),encoding='utf-8')
    print(output/'index.html')


if __name__=='__main__':
    main()
