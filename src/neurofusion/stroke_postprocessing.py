"""Fixed physical-size component filter for development experiments only."""
import numpy as np
from scipy import ndimage


def threshold_components(probability,voxel_ml,threshold=.55,minimum_ml=.01):
    p=np.asarray(probability)
    if p.ndim!=3 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Finite 3D probabilities in [0,1] required')
    if not np.isfinite(voxel_ml) or voxel_ml<=0 or not 0<threshold<1 or not np.isfinite(minimum_ml) or minimum_ml<0:
        raise ValueError('Invalid threshold or physical scale')
    labels,_=ndimage.label(p>=threshold,structure=np.ones((3,3,3),dtype=bool))
    counts=np.bincount(labels.ravel());keep=counts*voxel_ml>=minimum_ml;keep[0]=False
    return keep[labels]
