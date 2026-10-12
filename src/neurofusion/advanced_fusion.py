"""Separate modality encoders and explicitly experimental ensemble uncertainty."""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from neurofusion.segmentation import block


def inference_members(*,has_dwi,has_adc,experimental=False):
    if not has_dwi:
        raise ValueError('DWI required; ADC-only failed development evaluation')
    names=['dwi-component-001']
    if experimental:
        if has_adc:names.append('dwi-adc-002')
        names.append('separate-encoder-001')
    return names


def modality_input(dwi=None,adc=None):
    present=[x for x in (dwi,adc) if x is not None]
    if not present:raise ValueError('At least one modality is required')
    shape=present[0].shape
    if len(shape)!=3 or any(x.shape!=shape or not np.isfinite(x).all() for x in present):
        raise ValueError('Finite aligned 3D modalities required')
    return np.stack([np.zeros(shape,dtype=np.float32) if x is None else np.asarray(x,dtype=np.float32)
                     for x in (dwi,adc)]+[np.full(shape,x is not None,dtype=np.float32) for x in (dwi,adc)])


class Encoder(nn.Module):
    def __init__(self):
        super().__init__();self.a=block(1,8);self.down=nn.Conv3d(8,8,2,stride=2);self.b=block(8,16)
    def forward(self,x):
        a=self.a(x);return a,self.b(self.down(a))


class SeparateEncoderUNet(nn.Module):
    def __init__(self):
        super().__init__();self.dwi=Encoder();self.adc=Encoder()
        self.fuse1=nn.Conv3d(18,8,1);self.fuse2=nn.Conv3d(34,16,1)
        self.down=nn.Conv3d(16,16,2,stride=2);self.bottom=block(16,32)
        self.d2=block(48,16);self.d1=block(24,8);self.head=nn.Conv3d(8,1,1)
    def forward(self,x):
        if x.ndim!=5 or x.shape[1]!=4:raise ValueError('Two modalities and two availability channels required')
        availability=x[:,2:].amax(dim=(2,3,4),keepdim=True)
        if torch.any(availability.sum(1)==0):raise ValueError('No available modality')
        levels=[]
        for i,encoder in enumerate((self.dwi,self.adc)):
            gate=availability[:,i:i+1]
            a,b=encoder(x[:,i:i+1]*gate);levels.append((a*gate,b*gate))
        def fuse(level,layer):
            shape=levels[0][level].shape[2:]
            return layer(torch.cat([levels[0][level],levels[1][level],availability.expand(-1,-1,*shape)],1))
        a=fuse(0,self.fuse1);b=fuse(1,self.fuse2);c=self.bottom(self.down(b))
        d=self.d2(torch.cat([F.interpolate(c,size=b.shape[2:],mode='nearest'),b],1))
        return self.head(self.d1(torch.cat([F.interpolate(d,size=a.shape[2:],mode='nearest'),a],1)))


def ensemble_probabilities(members):
    arrays=np.asarray(members,dtype=np.float32)
    if arrays.ndim<2 or arrays.shape[0]<1 or not np.isfinite(arrays).all() or np.any((arrays<0)|(arrays>1)):
        raise ValueError('Valid probability members required')
    return arrays.mean(0),arrays.var(0)


def entropy(probability):
    p=np.asarray(probability,dtype=np.float64)
    if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probabilities')
    p=np.clip(p,1e-7,1-1e-7)
    return -(p*np.log(p)+(1-p)*np.log1p(-p))


def temperature_scale(probability,temperature):
    if not np.isfinite(temperature) or temperature<=0:raise ValueError('Positive temperature required')
    entropy(probability) # Validate rather than silently clipping invalid input.
    p=np.clip(np.asarray(probability,dtype=np.float64),1e-7,1-1e-7)
    logits=np.clip((np.log(p)-np.log1p(-p))/temperature,-50,50)
    return 1/(1+np.exp(-logits))


def reliability(probability,target):
    p=np.asarray(probability,dtype=np.float64);y=np.asarray(target)
    entropy(p)
    if p.shape!=y.shape or not p.size or not np.isin(y,[0,1]).all():raise ValueError('Matching binary targets required')
    p=np.clip(p,1e-7,1-1e-7)
    bins=np.minimum((p*10).astype(int),9);ece=0.
    for b in range(10):
        selected=bins==b
        if selected.any():ece+=selected.mean()*abs(p[selected].mean()-y[selected].mean())
    return {'nll':float(-(y*np.log(p)+(1-y)*np.log1p(-p)).mean()),'brier':float(np.square(p-y).mean()),'ece':float(ece)}
