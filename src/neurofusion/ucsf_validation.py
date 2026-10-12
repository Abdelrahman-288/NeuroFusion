"""Native-grid development validation for the numeric UCSF foreground task."""
import numpy as np
import nibabel as nib
from neurofusion.external_adapter import restore_probabilities
from neurofusion.native_metrics import native_binary_metrics
from neurofusion.specialist_plan import numeric_foreground


def score_native(probabilities, geometry, reference, threshold=0.5):
    restored = restore_probabilities(probabilities, geometry)
    prediction = nib.Nifti1Image((restored.get_fdata() >= threshold).astype(np.uint8), restored.affine)
    prediction.header.set_xyzt_units('mm')
    truth = nib.Nifti1Image(numeric_foreground(reference.get_fdata()).astype(np.uint8), reference.affine, reference.header.copy())
    return native_binary_metrics(prediction, truth), prediction


def aggregate_cases(cases):
    if not cases or len({c['patient_id'] for c in cases}) != len(cases):
        raise ValueError('This pilot requires exactly one exam per patient')
    result = {'patients': len(cases), 'empty_states': {}}
    for c in cases:
        state = c['metrics']['empty_state']
        result['empty_states'][state] = result['empty_states'].get(state, 0) + 1
    for key in ('dice', 'iou', 'voxel_recall', 'voxel_precision', 'absolute_volume_error_ml'):
        values = [c['metrics'][key] for c in cases if c['metrics'][key] is not None]
        result[key] = {'mean': float(np.mean(values)) if values else None, 'defined': len(values), 'undefined': len(cases)-len(values)}
    return result
