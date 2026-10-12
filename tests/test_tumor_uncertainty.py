import numpy as np
import pytest
from neurofusion.tumor_uncertainty import binary_scale,binary_scores,selective_summary


def test_temperature_preserves_decision_and_identity():
    p=np.asarray([0.,.01,.49,.5,.51,.99,1.])
    assert np.allclose(binary_scale(p,1),p,atol=1e-11)
    for t in (.5,2,4):assert np.array_equal(binary_scale(p,t)>=.5,p>=.5)


def test_binary_metrics_known_answer():
    result=binary_scores(np.asarray([.5,.5]),np.asarray([0,1]))
    assert result['nll']==pytest.approx(np.log(2))
    assert result['brier']==pytest.approx(.25)
    assert result['ece']==pytest.approx(0)
    with pytest.raises(ValueError):binary_scores(np.asarray([np.nan]),np.asarray([1]))


def test_abstention_uses_fit_only_threshold_and_rejects_empty_acceptance():
    result=selective_summary([.1,.2,.3,.4],[.1,.2,.9],[0,0,1])
    assert result['threshold']==pytest.approx(.34)
    assert result['coverage']==pytest.approx(2/3)
    assert result['accepted_risk']==0 and result['passed']
    result=selective_summary([.1,.2],[.8,.9],[0,1])
    assert result['accepted_risk'] is None and not result['passed']


def test_abstention_cannot_pass_if_it_keeps_worse_predictions():
    assert not selective_summary([.1,.2,.3],[.1,.2,.9],[1,1,0])['passed']
