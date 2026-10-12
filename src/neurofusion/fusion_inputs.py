"""Label-free native-grid input contract for experimental DWI/ADC inference."""
import nibabel as nib
import numpy as np
from nibabel.orientations import io_orientation,ornt_transform,axcodes2ornt


def prepare_inputs(dwi_path=None,adc_path=None):
    if dwi_path is None and adc_path is None:raise ValueError('At least one modality required')
    images={};arrays={}
    for key,path in [('dwi',dwi_path),('adc',adc_path)]:
        if path is None:continue
        original=nib.load(path)
        if len(original.shape)!=3 or max(original.shape)>512 or np.prod(original.shape)>16000000:
            raise ValueError('Expected bounded 3D MRI volume')
        if original.header.get_xyzt_units()[0]!='mm' or not np.isfinite(original.affine).all() or abs(np.linalg.det(original.affine[:3,:3]))<1e-8:
            raise ValueError('Valid geometry in millimeters required')
        q,qc=original.get_qform(coded=True);s,sc=original.get_sform(coded=True)
        if qc and sc and not np.allclose(q,s,atol=1e-4,rtol=0):raise ValueError('Conflicting orientation forms')
        canonical=nib.as_closest_canonical(original);values=canonical.get_fdata(dtype=np.float32)
        selected=values[values!=0]
        if not np.isfinite(values).all() or not len(selected) or selected.std()<1e-8:raise ValueError('Finite variable intensities required')
        normalized=np.zeros_like(values);normalized[values!=0]=(selected-selected.mean())/selected.std()
        arrays[key]=normalized;images[key]=(original,canonical)
    reference='dwi' if 'dwi' in images else 'adc'
    original,canonical=images[reference]
    for _,other in images.values():
        if other.shape!=canonical.shape or not np.allclose(other.affine,canonical.affine,atol=1e-4,rtol=0):raise ValueError('Modalities require a shared physical grid; registration is not automatic')
    meta={'original_shape':list(original.shape),'original_affine':original.affine.tolist(),
          'canonical_shape':list(canonical.shape),'canonical_affine':canonical.affine.tolist(),
          'xyzt_units':list(original.header.get_xyzt_units()),
          'inverse_orientation':ornt_transform(axcodes2ornt(('R','A','S')),io_orientation(original.affine)).tolist(),
          'reference_modality':reference,'modality_identity':'User supplied, not automatically verified'}
    return arrays,meta
