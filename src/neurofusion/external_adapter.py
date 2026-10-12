"""Development-only 3D-to-2D adapter with explicit reversible geometry."""
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image

from neurofusion.pdgm import audit_volume_pair


def prepare_pair(image_path, mask_path, *, allowed_labels, size=128):
    """Keep every canonical slice. Label meanings are deliberately not inferred."""
    if type(size) is not int or not 16 <= size <= 512:
        raise ValueError('Output size must be an integer between 16 and 512')
    if any(type(v) is not int or not 0 <= v <= 65535 for v in allowed_labels):
        raise ValueError('Label IDs must fit uint16')
    audit = audit_volume_pair(image_path, mask_path, allowed_labels=allowed_labels)
    original = nib.load(str(image_path))
    canonical = nib.as_closest_canonical(original)
    mask = nib.as_closest_canonical(nib.load(str(mask_path)))
    if canonical.shape[2]*size*size > 64_000_000:
        raise ValueError('Prepared slice allocation exceeds 64 million pixels')
    basis = canonical.affine[:3, :3]
    basis = basis / np.linalg.norm(basis, axis=0)
    if not np.allclose(basis.T @ basis, np.eye(3), atol=1e-4, rtol=0):
        raise ValueError('Sheared voxel grids require an explicit resampling policy')
    values = canonical.get_fdata(dtype=np.float32)
    labels = mask.get_fdata(dtype=np.float32).astype(np.uint16)
    nonzero = values != 0
    low, high = np.percentile(values[nonzero], [1, 99])
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError('Nonzero intensity percentile range is degenerate')
    scaled = np.where(nonzero, np.clip((values-low)/(high-low), 0, 1), 0)
    scaled = np.rint(scaled*255).astype(np.uint8)
    spacing = nib.affines.voxel_sizes(canonical.affine)
    # Canonical X is the column axis and Y is the row axis for exported slices.
    width_mm, height_mm = values.shape[0]*spacing[0], values.shape[1]*spacing[1]
    factor = size/max(width_mm, height_mm)
    width, height = max(1, round(width_mm*factor)), max(1, round(height_mm*factor))
    left, top = (size-width)//2, (size-height)//2
    images = np.zeros((values.shape[2], 1, size, size), dtype=np.uint8)
    masks = np.zeros((values.shape[2], size, size), dtype=np.uint16)
    lost_slices = []
    for z in range(values.shape[2]):
        im = Image.fromarray(scaled[:, :, z].T).resize((width, height), Image.Resampling.BILINEAR)
        label = Image.fromarray(labels[:, :, z].T).resize((width, height), Image.Resampling.NEAREST)
        images[z, 0, top:top+height, left:left+width] = np.asarray(im)
        masks[z, top:top+height, left:left+width] = np.asarray(label)
        lost = sorted(set(np.unique(labels[:, :, z])) - set(np.unique(masks[z])) - {0})
        if lost:
            lost_slices.append({'canonical_z': z, 'lost_label_ids': [int(v) for v in lost]})
    metadata = {
        'adapter_version': 'external-slice-v1', 'purpose': 'import development only',
        'evaluation_ready': False, 'label_semantics_verified': False,
        'native_shape': list(original.shape), 'native_affine': original.affine.tolist(),
        'canonical_shape': list(canonical.shape), 'canonical_affine': canonical.affine.tolist(),
        'native_orientation': nib.orientations.io_orientation(original.affine).tolist(),
        'canonical_orientation': nib.orientations.io_orientation(canonical.affine).tolist(),
        'slice_indices': list(range(values.shape[2])), 'size': size,
        'resize_wh': [width, height], 'offset_xy': [left, top],
        'intensity': {'method': 'whole-volume nonzero p1/p99, clip, uint8; zero background retained',
                      'low': float(low), 'high': float(high)},
        'label_policy': 'Retain numeric IDs with nearest-neighbor resize; no binary target mapping',
        'lost_label_slices': lost_slices, 'source_audit': audit,
        'limitations': ['Not the BRISC JPEG acquisition pipeline; domain shift unmeasured',
                       'Canonical voxel-axis slices; oblique scans are not resampled into true anatomical planes',
                       'Resizing is lossy; native-grid reconstruction restores geometry, not lost image detail',
                       'Whole-volume label semantics and external cohort independence remain unverified'],
    }
    return images, masks, metadata


def restore_probabilities(probabilities, metadata):
    """Remove padding, resize each slice, undo canonical axis permutation/flips."""
    expected = (metadata['canonical_shape'][2], metadata['size'], metadata['size'])
    p = np.asarray(probabilities, dtype=np.float32)
    if p.shape != expected or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Expected finite probabilities in [0,1] for every canonical slice')
    width, height = metadata['resize_wh']
    left, top = metadata['offset_xy']
    canonical = np.empty(metadata['canonical_shape'], dtype=np.float32)
    for z in metadata['slice_indices']:
        crop = p[z, top:top+height, left:left+width]
        restored = Image.fromarray(crop).resize(tuple(metadata['canonical_shape'][:2]), Image.Resampling.BILINEAR)
        canonical[:, :, z] = np.asarray(restored).T
    transform = nib.orientations.ornt_transform(np.asarray(metadata['canonical_orientation']),
                                               np.asarray(metadata['native_orientation']))
    native = nib.orientations.apply_orientation(canonical, transform)
    if tuple(native.shape) != tuple(metadata['native_shape']):
        raise ValueError('Native reconstruction shape mismatch')
    result = nib.Nifti1Image(native, np.asarray(metadata['native_affine']))
    result.header.set_xyzt_units('mm')
    return result
