import numpy as np
import pytest
from neurofusion.uncertainty_policy import uncertainty_decision,CLASSIFIER_SHA,CUTOFF


def test_low_confidence_withheld_and_high_confidence_not_certified():
    models={'tumor_classifier':CLASSIFIER_SHA}
    low=uncertainty_decision('tumor-image',models,[.25]*4)
    high=uncertainty_decision('tumor-image',models,[.97,.01,.01,.01])
    assert low['classification_development_screen']['decision']=='withhold'
    assert high['classification_development_screen']['decision']=='within_development_cutoff'
    for r in (low,high):assert r['decision']=='abstain' and not r['reliable_prediction_available']


def test_changed_checkpoint_and_stroke_do_not_reuse_cutoff():
    for task,models in [('tumor-image',{'tumor_classifier':'changed'}),('stroke-dwi',{})]:
        r=uncertainty_decision(task,models,[.25]*4)
        assert r['classification_development_screen']['decision']=='unavailable'
        assert r['decision']=='abstain'


def test_cutoff_and_invalid_probabilities():
    models={'tumor_classifier':CLASSIFIER_SHA}
    p=[1-CUTOFF,CUTOFF/3,CUTOFF/3,CUTOFF/3]
    assert uncertainty_decision('tumor-image',models,p)['classification_development_screen']['decision']=='within_development_cutoff'
    for p in ([np.nan,0,0,1],[1,1,1,1],[-1,0,1,1],[1]):
        with pytest.raises(ValueError):uncertainty_decision('tumor-image',models,p)
