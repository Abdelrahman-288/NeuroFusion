"""Render stored overfit arrays; all panels refer to the SAME training patch."""
import argparse
from pathlib import Path
import numpy as np
from preview_studies import png

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args()
output=args.run/'training-patch-comparison.png'
if output.exists():
    parser.error('Preview already exists')
with np.load(args.run/'patch-results.npz') as data:
    x=data['image']; y=data['reference']>0; p=data['probability']>=.5
z=int(np.argmax(y.sum(axis=(0,1))))
low,high=np.percentile(x,[1,99])
gray=(np.clip((np.rot90(x[:,:,z])-low)/max(high-low,1e-8),0,1)*255).astype(np.uint8)
plain=np.repeat(gray[:,:,None],3,axis=2)
panels=[plain]
for values in [y,p]:
    overlay=plain.copy()
    mask=np.rot90(values[:,:,z])
    overlay[mask]=(.4*overlay[mask]+.6*np.array([255,60,60])).astype(np.uint8)
    panels.append(overlay)
png(output,np.repeat(np.repeat(np.concatenate(panels,axis=1),5,axis=0),5,axis=1))
print(output)
