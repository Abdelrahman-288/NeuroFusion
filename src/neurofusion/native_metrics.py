"""Binary segmentation metrics on matching native NIfTI grids; no resampling."""
import numpy as np


def native_binary_metrics(prediction, reference):
    """Require binary NIfTI inputs with explicit millimeter units.

    Both-empty Dice/IoU are undefined (None), not perfect scores. Undefined
    precision/recall are also None. Report empty-case counts when aggregating.
    These are geometric annotation comparisons, not diagnostic accuracy.
    """
    arrays = []
    for volume in (prediction, reference):
        if len(volume.shape) != 3 or min(volume.shape) < 1 or np.prod(volume.shape) > 50_000_000:
            raise ValueError('Expected bounded nonempty 3D grid')
        if volume.header.get_xyzt_units()[0] != 'mm':
            raise ValueError('Explicit millimeter spatial units required')
        affine = volume.affine
        if not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3,:3])) < 1e-8:
            raise ValueError('Invalid spatial affine')
        q, qc = volume.get_qform(coded=True)
        s, sc = volume.get_sform(coded=True)
        if qc and sc and not np.allclose(q,s,atol=1e-4,rtol=0):
            raise ValueError('Conflicting coded spatial transforms')
        values = volume.get_fdata(dtype=np.float32)
        if not np.isfinite(values).all() or not np.isin(values,[0,1]).all():
            raise ValueError('Explicit binary masks required; no implicit threshold or label mapping')
        arrays.append(values.astype(bool))
    if prediction.shape != reference.shape or not np.allclose(prediction.affine,reference.affine,atol=1e-4,rtol=0):
        raise ValueError('Native grids differ; explicit reconstruction required')
    pred, truth = arrays
    tp = int((pred & truth).sum())
    fp = int((pred & ~truth).sum())
    fn = int((~pred & truth).sum())
    tn = int((~pred & ~truth).sum())
    pn, rn = tp+fp, tp+fn
    voxel_ml = float(abs(np.linalg.det(reference.affine[:3,:3]))/1000)
    state = 'both_empty' if not pn and not rn else 'reference_empty' if not rn else 'prediction_empty' if not pn else 'both_nonempty'
    return {'empty_state':state, 'tp':tp, 'fp':fp, 'fn':fn, 'tn':tn,
        'dice':2*tp/(pn+rn) if pn+rn else None,
        'iou':tp/(tp+fp+fn) if tp+fp+fn else None,
        'voxel_recall':tp/rn if rn else None,
        'voxel_precision':tp/pn if pn else None,
        'voxel_ml':voxel_ml, 'reference_ml':rn*voxel_ml,
        'prediction_ml':pn*voxel_ml, 'signed_volume_error_ml':(pn-rn)*voxel_ml,
        'absolute_volume_error_ml':abs(pn-rn)*voxel_ml}
