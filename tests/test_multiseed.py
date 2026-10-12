import pytest
from neurofusion.multiseed import statistics,screen

G={'mean_clean_accuracy_delta_pp_min':-1,'mean_clean_macro_f1_delta_min':-.01,'each_class_mean_clean_recall_delta_pp_min':-5,'mean_perturbed_accuracy_delta_pp_min':2,'each_seed_clean_accuracy_delta_pp_min':-3}

def test_sample_deviation():
    assert statistics([1,2,3])=={'mean':2.,'sample_std':1.,'min':1.,'max':3.}
    with pytest.raises(ValueError):statistics([1])

def test_class_regression_blocks_screen_even_with_stress_gain():
    result=screen([0,0,0],[0,0,0],{'a':[-6,-6,-6]},[10,10,10],G)
    assert not result['development_screen_passed']
    assert not result['checks']['each_class_mean_clean_recall']

def test_passing_screen_never_promotes():
    result=screen([0,0,0],[0,0,0],{'a':[0,0,0]},[3,3,3],G)
    assert result['development_screen_passed'] and not result['automatic_promotion']
