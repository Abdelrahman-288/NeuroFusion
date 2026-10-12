"""Strict native-grid DWI/ADC early fusion for development studies."""
import nibabel as nib
import numpy as np
from neurofusion.cohort import digest


def load_aligned_adc(path, metadata):
    """Reject incompatible geometry; matching grids alone do not prove anatomy alignment."""
    image=nib.as_closest_canonical(nib.load(path))
    units=image.header.get_xyzt_units()[0]
    if units=='unknown' or units!=metadata['xyzt_units'][0]:
        raise ValueError('ADC spatial units must be known and match DWI')
    if image.shape!=tuple(metadata['canonical_shape']) or not np.allclose(image.affine,metadata['canonical_affine'],rtol=0,atol=1e-4):
        raise ValueError('ADC must share the DWI physical grid; registration required')
    values=image.get_fdata(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError('ADC contains nonfinite intensities')
    foreground=values!=0
    selected=values[foreground]
    if selected.size==0 or float(selected.std())<1e-8:
        raise ValueError('ADC has no usable foreground variation')
    mean,std=float(selected.mean()),float(selected.std())
    normalized=np.zeros_like(values)
    normalized[foreground]=(selected-mean)/std
    return normalized,{'mean':mean,'std':std,'normalization':'per-image nonzero zscore'}


def load_fusion_study(store,study):
    # Resolve the authoritative, development-only entry before using an ADC path.
    authoritative,_,_=store._paths(study)
    path=(store.root/authoritative['files']['adc']['path']).resolve()
    if not path.is_relative_to(store.root):
        raise ValueError('ADC path escapes dataset root')
    if digest(path)!=authoritative['files']['adc']['sha256']:
        raise ValueError('ADC changed since manifest creation')
    dwi,mask,metadata=store.load(authoritative)
    adc,statistics=load_aligned_adc(path,metadata)
    return np.stack([dwi,adc]),mask,{**metadata,'channels':['dwi','adc'],
        'adc_sha256':authoritative['files']['adc']['sha256'],'adc_statistics':statistics}
