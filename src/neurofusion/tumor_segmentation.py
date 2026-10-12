"""BRISC binary tumor segmentation with an explicit near-binary mask policy."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
from neurofusion.cohort import digest
from neurofusion.tumor import load_partition


def binary_mask(values):
    if values.ndim!=2 or values.dtype!=np.uint8 or np.any((values>10)&(values<246)):
        raise ValueError('Mask must be uint8 2D with intensities in 0-10 or 246-255')
    return (values>=128).astype(np.uint8)


def load_segmentation(root,splits,partition,keep_native=True):
    # Reuse the development-only loader, fingerprints and group-overlap checks.
    images,_,rows=load_partition(root,splits,partition)
    root=Path(root).resolve()
    publisher={r['relative_path'].replace('\\','/'):r for r in json.loads((root/'manifest.json').read_text())}
    selected=[]; small=[]; native=[]; records=[]
    for i,row in enumerate(rows):
        if row['label']=='no_tumor': continue # Missing annotation is not an empty mask.
        name=Path(row['path']).stem
        rel=f'segmentation_task/{row["source_split"]}/masks/{name}.png'
        if rel not in publisher: raise ValueError('Tumor image has no supplied mask')
        path=(root/rel).resolve()
        if not path.is_relative_to(root) or digest(path)!=publisher[rel]['sha256']:
            raise ValueError('Mask source checksum/path mismatch')
        with Image.open(path) as image:
            if image.mode!='L': raise ValueError('Expected grayscale mask')
            values=np.asarray(image)
        if list(values.shape)!=row['shape'][:2]: raise ValueError('Image-mask dimensions differ')
        mask=binary_mask(values)
        if not mask.any(): raise ValueError('Unexpected empty tumor mask')
        resized=np.asarray(Image.fromarray(mask).resize((128,128),Image.Resampling.NEAREST))
        if not resized.any(): raise ValueError('Lesion disappeared during mask resizing')
        selected.append(i); small.append(resized)
        if keep_native: native.append(mask)
        records.append({**row,'mask_path':rel,'mask_sha256':publisher[rel]['sha256']})
    if not selected: raise ValueError('No segmentation pairs')
    return images[selected],np.stack(small)[:,None],native,records


def block(a,b):
    return nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.GroupNorm(4,b),nn.LeakyReLU(.1),
                         nn.Conv2d(b,b,3,padding=1),nn.GroupNorm(4,b),nn.LeakyReLU(.1))


class TumorUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.e1=block(1,8); self.down1=nn.Conv2d(8,8,2,stride=2)
        self.e2=block(8,16); self.down2=nn.Conv2d(16,16,2,stride=2)
        self.bottom=block(16,32); self.d2=block(48,16); self.d1=block(24,8); self.head=nn.Conv2d(8,1,1)

    def forward(self,x):
        a=self.e1(x); b=self.e2(self.down1(a)); c=self.bottom(self.down2(b))
        d=self.d2(torch.cat([F.interpolate(c,size=b.shape[2:],mode='nearest'),b],1))
        return self.head(self.d1(torch.cat([F.interpolate(d,size=a.shape[2:],mode='nearest'),a],1)))


def segmentation_loss(logits,target):
    probs=logits.float().sigmoid()
    dice=(2*(probs*target).sum((1,2,3))+1)/(probs.sum((1,2,3))+target.sum((1,2,3))+1)
    return F.binary_cross_entropy_with_logits(logits.float(),target)+1-dice.mean()


def native_probability(probability,shape):
    return np.asarray(Image.fromarray(probability.astype(np.float32)).resize((shape[1],shape[0]),Image.Resampling.BILINEAR))


def mask_metrics(probability,truth):
    if probability.shape!=truth.shape or not np.isfinite(probability).all(): raise ValueError('Invalid probability geometry/values')
    prediction=probability>=.5; truth=truth>0
    intersection=int((prediction&truth).sum()); p=int(prediction.sum()); t=int(truth.sum())
    return {'dice':2*intersection/(p+t) if p+t else 1.,'iou':intersection/(p+t-intersection) if p+t-intersection else 1.,
            'reference_pixels':t,'predicted_pixels':p,'false_positive_pixels':int((prediction&~truth).sum())}
