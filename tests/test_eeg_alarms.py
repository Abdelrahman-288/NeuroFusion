import numpy as np
import pytest
from neurofusion.eeg_alarms import confirmed_windows,score_policy,aggregate,apply_alarm_policy,normalize_windows


def test_confirmation_is_causal_and_resets():
    p=[.9,.9,.1,.9,.9,.9]
    assert confirmed_windows(p,.8,2).tolist()==[0,1,0,0,1,1]
    for i in range(1,len(p)+1):assert np.array_equal(confirmed_windows(p[:i],.8,2),confirmed_windows(p,.8,2)[:i])


def test_no_backdating_and_short_event_misses():
    r=score_policy([.9]*4,[(0,5)],16,.8,2)
    assert r['decision_times_seconds']==[8]
    assert r['matched_events']==1 and r['timely_matched_events']==0
    r=score_policy([.9]*4,[(1,15)],16,.8,2)
    assert r['timely_latency_seconds']==[7]


def test_no_cross_record_confirmation_and_background_burden():
    assert confirmed_windows([.9],.8,2).tolist()==[0]
    r=score_policy([.9,.9,0,0],[],16,.8,2)
    assert r['false_alarm_events']==1 and r['background_alarm_seconds']==4
    assert aggregate([r,r])['false_alarm_events']==2
    with pytest.raises(ValueError):confirmed_windows([float('nan')],.8,2)
    with pytest.raises(ValueError):confirmed_windows([.9],.8,0)


def test_policy_requires_checkpoint_binding_and_passed_checks():
    p=dict(schema_version=1,checkpoint_sha256='a'*64,window_seconds=4,development_checks_passed=True,threshold=.8,consecutive_windows=2)
    assert apply_alarm_policy([.9,.9],p,'a'*64).tolist()==[0,1]
    with pytest.raises(ValueError):apply_alarm_policy([.9,.9],p,'b'*64)
    p['development_checks_passed']=False
    with pytest.raises(ValueError):apply_alarm_policy([.9,.9],p,'a'*64)


def test_normalization_never_uses_other_windows():
    x=np.random.default_rng(42).normal(size=(3,6,512)).astype(np.float32)
    result=normalize_windows(x)
    assert np.array_equal(normalize_windows(x[:1]),result[:1])
    np.testing.assert_allclose(normalize_windows(x*2+3),result,atol=2e-6)
    assert not normalize_windows(np.zeros((1,6,512),dtype=np.float32)).any()
    with pytest.raises(ValueError):normalize_windows(np.zeros((1,3,512)))
