"""Candidate BraTS numeric unions for annotation QA, with a scoring gate."""
import numpy as np


def candidate_regions(mask):
    """Return candidate unions; this function does not certify source semantics."""
    values = np.asarray(mask)
    if values.ndim != 3 or not values.size or not np.isfinite(values).all():
        raise ValueError('Expected a nonempty finite 3D mask')
    if not np.isin(values, [0, 1, 2, 4]).all():
        raise ValueError('Unexpected numeric labels; do not round or remap silently')
    return {'WT': np.isin(values, [1, 2, 4]),
            'TC': np.isin(values, [1, 4]), 'ET': values == 4}


def require_evaluation_contract(contract):
    """Reject an unreviewed mapping or incompatible binary model target."""
    if contract.get('version_specific_mapping_confirmed') is not True:
        raise ValueError('Version-specific mapping confirmation is pending')
    if contract.get('current_model_compatibility', {}).get('region_equivalence_verified') is not True:
        raise ValueError('Model target equivalence is unverified')
    if contract.get('evaluation_ready') is not True:
        raise ValueError('Evaluation protocol is not ready')
