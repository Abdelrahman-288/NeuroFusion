"""Compare saved real validation predictions with reference masks on selected slices."""
import argparse
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from preview_studies import png

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args()
config=json.loads((args.run/'config.json').read_text())
output=args.run/'prediction-preview'
if output.exists():
    parser.error('Prediction preview already exists')
output.mkdir()
cards=[]
for subject in config['validation_subjects']:
    image=nib.load(args.run/'prepared'/subject/'dwi.nii.gz').get_fdata()
    reference=nib.load(args.run/'prepared'/subject/'mask.nii.gz').get_fdata()>0
    probability=nib.as_closest_canonical(nib.load(args.run/'predictions'/f'{subject}-probability.nii.gz')).get_fdata()
    if image.shape!=probability.shape:
        raise ValueError('Prediction grid mismatch')
    prediction=probability>=.5
    slices=sorted({int(np.argmax(reference.sum(axis=(0,1)))),int(np.argmax(prediction.sum(axis=(0,1))))})
    low,high=np.percentile(image[image!=0],[1,99])
    for z in slices:
        gray=(np.clip((np.rot90(image[:,:,z])-low)/max(high-low,1e-8),0,1)*255).astype(np.uint8)
        plain=np.repeat(gray[:,:,None],3,axis=2)
        panels=[plain]
        for label in (reference,prediction):
            overlay=plain.copy()
            mask=np.rot90(label[:,:,z])
            overlay[mask]=(.45*overlay[mask]+.55*np.array([255,60,60])).astype(np.uint8)
            panels.append(overlay)
        name=f'{subject}-z{z}.png'
        png(output/name,np.concatenate(panels,axis=1))
        cards.append(f'<h2>{html.escape(subject)} — slice {z}</h2><p>Left: DWI · Middle: supplied reference · Right: model prediction at 0.5</p><img src="{name}" style="width:100%;image-rendering:pixelated" alt="DWI reference and prediction comparison">')
(output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>NeuroFusion preliminary predictions</title><style>body{font:17px system-ui;max-width:1000px;margin:40px auto;padding:20px;color:#173348}</style><h1>Preliminary validation predictions</h1><p>Small debugging run, not a clinical result. Selected slices with maximum reference and predicted area, not a full-volume review. Voxel-based display aspect.</p>'+''.join(cards),encoding='utf-8')
print(output/'index.html')
