"""Bounded intensity-similarity screening; not proof of patient independence."""
import numpy as np
from scipy.ndimage import zoom


def fingerprint(values, size=24):
    values=np.asarray(values,dtype=np.float32)
    if values.ndim!=3 or min(values.shape)<2 or not np.isfinite(values).all():
        raise ValueError('Finite nondegenerate 3D volume required')
    small=zoom(values,[size/n for n in values.shape],order=1,prefilter=False)
    selected=small!=0
    if np.count_nonzero(selected)<8 or np.std(small[selected])<=1e-8:
        raise ValueError('Insufficient intensity variation')
    result=np.zeros_like(small)
    result[selected]=(small[selected]-np.mean(small[selected]))/np.std(small[selected])
    vector=result.ravel().astype(np.float64)
    return vector/np.linalg.norm(vector)


def similarity(left,right):
    left,right=np.asarray(left),np.asarray(right)
    if left.shape!=right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError('Matching finite fingerprints required')
    if not np.isclose(np.linalg.norm(left),1) or not np.isclose(np.linalg.norm(right),1):
        raise ValueError('Normalized fingerprints required')
    return float(np.clip(np.dot(left,right),-1,1))
