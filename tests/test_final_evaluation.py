import pytest
from neurofusion.final_evaluation import REQUIRED,eligibility,require_executable


@pytest.mark.parametrize('gate',REQUIRED)
def test_each_prerequisite_fails_closed(gate):
    checks=dict.fromkeys(REQUIRED,True);checks[gate]=False
    assert not eligibility(checks)['eligible']
    with pytest.raises(ValueError):require_executable(dict(status='FROZEN_FOR_EXECUTION',models=[dict(checks=checks)]))


def test_empty_or_unfrozen_protocol_cannot_claim_completion():
    with pytest.raises(ValueError):require_executable(dict(status='FROZEN_FOR_EXECUTION',models=[]))
    with pytest.raises(ValueError):require_executable(dict(status='BLOCKED_NOT_FROZEN_FOR_EXECUTION',models=[]))
    assert not eligibility({})['eligible']


def test_execution_requires_actual_artifact_bindings():
    m=dict(checks=dict.fromkeys(REQUIRED,True))
    with pytest.raises(ValueError):require_executable(dict(status='FROZEN_FOR_EXECUTION',models=[m]))
    with pytest.raises(ValueError):eligibility({'invented':True})
