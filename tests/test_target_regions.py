import numpy as np
import pytest
from neurofusion.target_regions import candidate_regions, require_evaluation_contract


def test_nested_unions_with_distinct_numeric_ids():
    values = np.array([0,1,2,4]).reshape(2,2,1)
    r = candidate_regions(values)
    assert [int(r[k].sum()) for k in ('WT','TC','ET')] == [3,2,1]
    assert np.all(r['ET'] <= r['TC']) and np.all(r['TC'] <= r['WT'])
    assert r['WT'][1,0,0] and not r['TC'][1,0,0]


@pytest.mark.parametrize('value', [3, -1, 1.2, float('nan')])
def test_reject_unknown_fractional_or_nonfinite_ids(value):
    with pytest.raises(ValueError): candidate_regions(np.full((2,2,2),value))


def test_absent_regions_are_empty_not_healthy_diagnoses():
    assert all(not v.any() for v in candidate_regions(np.zeros((2,2,2))).values())


@pytest.mark.parametrize('missing', ['mapping','equivalence','ready'])
def test_each_evaluation_gate_is_required(missing):
    c={'version_specific_mapping_confirmed':missing!='mapping',
       'current_model_compatibility':{'region_equivalence_verified':missing!='equivalence'},
       'evaluation_ready':missing!='ready'}
    with pytest.raises(ValueError): require_evaluation_contract(c)
