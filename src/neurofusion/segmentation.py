"""Small native-grid DWI U-Net and label-independent sliding-window inference."""
import itertools
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


def block(a,b):
    return nn.Sequential(nn.Conv3d(a,b,3,padding=1),nn.GroupNorm(4,b),nn.LeakyReLU(.1),
                         nn.Conv3d(b,b,3,padding=1),nn.GroupNorm(4,b),nn.LeakyReLU(.1))


class CompactUNet(nn.Module):
    def __init__(self,in_channels=1):
        super().__init__()
        self.e1=block(in_channels,8)
        self.down1=nn.Conv3d(8,8,2,stride=2)
        self.e2=block(8,16)
        self.down2=nn.Conv3d(16,16,2,stride=2)
        self.bottom=block(16,32)
        self.d2=block(48,16)
        self.d1=block(24,8)
        self.head=nn.Conv3d(8,1,1)

    def forward(self,x):
        a=self.e1(x)
        b=self.e2(self.down1(a))
        c=self.bottom(self.down2(b))
        d=self.d2(torch.cat([F.interpolate(c,size=b.shape[2:],mode='nearest'),b],1))
        return self.head(self.d1(torch.cat([F.interpolate(d,size=a.shape[2:],mode='nearest'),a],1)))


def segmentation_loss(logits, target):
    probability=logits.float().sigmoid()
    soft_dice=(2*(probability*target).sum()+1)/(probability.sum()+target.sum()+1)
    return F.binary_cross_entropy_with_logits(logits.float(),target)+1-soft_dice


def component_coordinates(mask):
    """Group training foreground voxels by 26-connected component, once per study."""
    from scipy import ndimage
    labels,count=ndimage.label(mask>0,structure=ndimage.generate_binary_structure(3,3))
    boxes=ndimage.find_objects(labels)
    return [np.argwhere(labels[box]==i+1)+np.array([s.start for s in box])
            for i,box in enumerate(boxes)]


def sample_patch(image,mask,rng,size=32,components=None):
    if image.ndim not in (3,4) or image.shape[-3:]!=mask.shape:
        raise ValueError('Image spatial shape must match 3D mask')
    padding=[(0,max(0,size-s)) for s in mask.shape]
    image=np.pad(image,([(0,0)]+padding) if image.ndim==4 else padding)
    mask=np.pad(mask,padding)
    # Only training labels are used for sampling. Validation never calls this.
    positive=np.argwhere(mask>0)
    if len(positive) and rng.random()<.5:
        if components is None:
            center=positive[rng.integers(len(positive))]
        else:
            component=components[rng.integers(len(components))]
            center=component[rng.integers(len(component))]
    else:
        center=np.array([rng.integers(s) for s in mask.shape])
    start=np.maximum(0,np.minimum(center-size//2,np.array(mask.shape)-size))
    slices=tuple(slice(int(s),int(s)+size) for s in start)
    return image[((slice(None),)+slices) if image.ndim==4 else slices].copy(),mask[slices].copy()


@torch.inference_mode()
def predict_volume(model,image,device,patch=32,overlap=.5):
    if patch<4 or not 0<=overlap<1 or image.ndim not in (3,4) or not np.isfinite(image).all():
        raise ValueError('Invalid image, patch size or overlap')
    shape=image.shape[-3:]
    channels=image.ndim==4
    padding=[(0,max(0,patch-s)) for s in shape]
    padded=np.pad(image,([(0,0)]+padding) if channels else padding)
    stride=max(1,int(patch*(1-overlap)))
    positions=[]
    for length in padded.shape[-3:]:
        positions.append(sorted(set(list(range(0,length-patch+1,stride))+[length-patch])))
    total=np.zeros(padded.shape[-3:],dtype=np.float32)
    counts=np.zeros_like(total)
    model.eval()
    for start in itertools.product(*positions):
        region=tuple(slice(s,s+patch) for s in start)
        values=padded[(slice(None),)+region] if channels else padded[region][None]
        tensor=torch.from_numpy(values.copy())[None].to(device)
        result=model(tensor).float().sigmoid()[0,0].cpu().numpy()
        total[region]+=result
        counts[region]+=1
    if np.any(counts==0):
        raise RuntimeError('Sliding-window coverage gap')
    result=(total/counts)[tuple(slice(0,s) for s in shape)]
    if not np.isfinite(result).all():
        raise RuntimeError('Nonfinite inference result')
    return result


def metrics(probabilities,target,threshold=.5):
    prediction=probabilities>=threshold
    truth=target>0
    intersection=int((prediction & truth).sum())
    pred_count,truth_count=int(prediction.sum()),int(truth.sum())
    return {'dice':2*intersection/(pred_count+truth_count) if pred_count+truth_count else 1.,
            'voxel_recall':intersection/truth_count if truth_count else None,
            'voxel_precision':intersection/pred_count if pred_count else None,
            'false_positive_voxels':int((prediction & ~truth).sum()),
            'reference_voxels':truth_count,'predicted_voxels':pred_count}
