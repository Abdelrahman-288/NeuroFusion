"""Seeded training-only intensity augmentation on the normalized image grid."""
import numpy as np

POLICY = {'probability': .8, 'brightness': [.8, 1.2], 'contrast': [.8, 1.2],
          'contrast_center': .5, 'noise_sigma': [0., .03], 'seed': 1042}
CONTRAST_POLICY = {'name':'contrast-only-v1','probability':.3,'contrast':[.8,1.0],
                   'contrast_center':.5,'seed':1042}


def augment_contrast(images, rng):
    x=np.asarray(images,dtype=np.float32)
    if x.ndim!=4 or x.shape[1]!=1 or not np.isfinite(x).all() or x.min()<0 or x.max()>1:
        raise ValueError('Expected normalized NCHW grayscale images')
    shape=(len(x),1,1,1)
    active=rng.random(shape)<CONTRAST_POLICY['probability']
    contrast=rng.uniform(*CONTRAST_POLICY['contrast'],shape).astype(np.float32)
    return np.where(active,np.clip((x-.5)*contrast+.5,0,1),x).astype(np.float32)


def augment(images, rng):
    x=np.asarray(images,dtype=np.float32)
    if x.ndim!=4 or x.shape[1]!=1 or not np.isfinite(x).all() or x.min()<0 or x.max()>1:
        raise ValueError('Expected normalized NCHW grayscale images')
    shape=(len(x),1,1,1)
    active=rng.random(shape)<POLICY['probability']
    brightness=rng.uniform(*POLICY['brightness'],shape).astype(np.float32)
    contrast=rng.uniform(*POLICY['contrast'],shape).astype(np.float32)
    sigma=rng.uniform(*POLICY['noise_sigma'],shape).astype(np.float32)
    noise=rng.normal(size=x.shape).astype(np.float32)*sigma
    transformed=((x-.5)*contrast+.5)*brightness+noise
    return np.where(active,np.clip(transformed,0,1),x).astype(np.float32)
