import numpy as np
import pytest
from neurofusion.lesions import lesion_metrics


def test_perfect_and_empty():
    zero=np.zeros((5,5,5))
    r=lesion_metrics(zero,zero,.001)
    assert r['matched_pairs']==0 and r['lesion_recall'] is None and r['lesion_precision'] is None
    zero[1,1,1]=1;zero[3,3,3]=1
    r=lesion_metrics(zero,zero,.002)
    assert r['matched_pairs']==2 and r['lesion_f1']==1
    assert r['reference_details'][0]['volume_ml']==.002


def test_missed_and_spurious():
    truth=np.zeros((5,5,5));truth[0,0,0]=1
    pred=np.zeros_like(truth);pred[4,4,4]=1
    r=lesion_metrics(pred,truth,.001)
    assert r['missed_reference_lesions']==1 and r['unmatched_predicted_components']==1
    assert r['lesion_f1']==0


def test_threshold_boundary_matches_voxel_metrics():
    from neurofusion.segmentation import metrics
    truth=np.zeros((5,5,5));truth[0,0,0]=1
    probability=np.zeros_like(truth);probability[0,0,0]=.65;probability[4,4,4]=.55
    low=lesion_metrics(probability,truth,.001,threshold=.55)
    high=lesion_metrics(probability,truth,.001,threshold=.65)
    assert low['matched_pairs']==high['matched_pairs']==1
    assert low['no_overlap_predicted_components']==1
    assert high['no_overlap_predicted_components']==0
    assert metrics(probability,truth,.65)['dice']==1
    assert lesion_metrics(probability,truth,.001,threshold=.75)['missed_reference_lesions']==1


def test_merge_cannot_claim_two_true_positives():
    truth=np.zeros((7,7,7));truth[1,3,3]=1;truth[5,3,3]=1
    pred=np.zeros_like(truth);pred[1:6,3,3]=1
    r=lesion_metrics(pred,truth,.001)
    assert r['reference_lesions']==2 and r['matched_pairs']==1
    assert all(v['any_overlap'] for v in r['reference_details'])


def test_split_extra_component_is_unmatched():
    truth=np.zeros((7,7,7));truth[1:6,3,3]=1
    pred=np.zeros_like(truth);pred[1,3,3]=1;pred[5,3,3]=1
    r=lesion_metrics(pred,truth,.001)
    assert r['matched_pairs']==1 and r['unmatched_predicted_components']==1
    assert r['no_overlap_predicted_components']==0


def test_connectivity_and_stricter_overlap():
    truth=np.zeros((5,5,5));truth[1,1,1]=1;truth[2,2,2]=1
    assert lesion_metrics(truth,truth,.001,connectivity=26)['reference_lesions']==1
    assert lesion_metrics(truth,truth,.001,connectivity=6)['reference_lesions']==2
    pred=np.ones_like(truth)
    assert lesion_metrics(pred,truth,.001)['matched_pairs']==1
    assert lesion_metrics(pred,truth,.001,min_iou=.1)['matched_pairs']==0


@pytest.mark.parametrize('bad',[np.nan,1.1,-.1])
def test_bad_probabilities_rejected(bad):
    p=np.zeros((3,3,3));p[0,0,0]=bad
    with pytest.raises(ValueError):
        lesion_metrics(p,np.zeros_like(p),.001)
