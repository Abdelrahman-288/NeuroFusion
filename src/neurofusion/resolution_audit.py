"""Categorical mask roundtrip QA; these measurements are not model scores."""
import numpy as np
from PIL import Image
from scipy import ndimage


def compare_masks(reference, reconstructed):
    """Compare native-grid IDs using 26-connected components, separately per ID."""
    a, b = np.asarray(reference), np.asarray(reconstructed)
    if a.ndim != 3 or a.shape != b.shape or a.size == 0:
        raise ValueError('Expected matching nonempty 3D masks')
    for value in (a, b):
        if not np.isfinite(value).all() or np.any(value < 0) or np.any(value != np.rint(value)):
            raise ValueError('Expected finite nonnegative integer labels')
    rows = []
    for label in sorted((set(np.unique(a)) | set(np.unique(b))) - {0}):
        original, restored = a == label, b == label
        n, m = int(original.sum()), int(restored.sum())
        components, count = ndimage.label(original, structure=np.ones((3, 3, 3)))
        sizes = np.bincount(components.ravel())
        hits = set(np.unique(components[restored])) - {0}
        missing = [int(sizes[i]) for i in range(1, count+1) if i not in hits]
        rows.append({'label_id': int(label), 'native_voxels': n,
                     'roundtrip_voxels': m, 'voxel_delta': m-n,
                     'roundtrip_dice': 2*int((original & restored).sum())/(n+m),
                     'native_components_26': int(count),
                     'components_without_same_label_overlap': len(missing),
                     'missing_component_sizes_voxels': missing})
    return rows


def restore_categorical(prepared, metadata):
    """Undo letterboxing with nearest-neighbor IDs; return canonical XYZ mask.

    This intentionally differs from bilinear model-probability reconstruction.
    It isolates annotation sampling loss, without inference or target mapping.
    """
    shape = metadata['canonical_shape']
    masks = np.asarray(prepared)
    if masks.shape != (shape[2], metadata['size'], metadata['size']):
        raise ValueError('Prepared shape differs from geometry')
    if not np.issubdtype(masks.dtype, np.integer) or np.any(masks < 0) or np.any(masks > 65535):
        raise ValueError('Expected uint16-compatible integer IDs')
    width, height = metadata['resize_wh']
    left, top = metadata['offset_xy']
    if min(width, height) < 1 or min(left, top) < 0 or left+width > masks.shape[2] or top+height > masks.shape[1]:
        raise ValueError('Invalid crop geometry')
    restored = np.empty(shape, dtype=np.uint16)
    for z in range(shape[2]):
        crop = masks[z, top:top+height, left:left+width].astype(np.uint16)
        restored[:, :, z] = np.asarray(Image.fromarray(crop).resize(
            tuple(shape[:2]), Image.Resampling.NEAREST)).T
    return restored
