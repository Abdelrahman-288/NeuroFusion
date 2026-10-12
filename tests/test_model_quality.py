import copy
import pytest
from neurofusion.model_quality import compare_tumor, compare_stroke, paired_cases


def tumor():
    return [dict(path=str(i),group_id=str(i),label=c,reference_pixels=10,dice=.5,iou=.33,false_positive_pixels=5) for i,c in enumerate(['glioma','meningioma','pituitary'])]


def test_improved_overlap_cannot_hide_false_positives():
    a=tumor();b=copy.deepcopy(a)
    for r in b:r.update(dice=.7,iou=.5,false_positive_pixels=6)
    result=compare_tumor(a,b)
    assert not result['development_screen_passed'] and result['checks']['mean_dice_improves']
    for r in b:r['false_positive_pixels']=4
    assert compare_tumor(a,b)['development_screen_passed']
    assert not compare_tumor(a,b)['promotion_permitted']


def test_case_identity_mismatch_and_nan_rejected():
    a=tumor();b=copy.deepcopy(a);b[0]['group_id']='other'
    with pytest.raises(ValueError):paired_cases(a,b,'path')
    b=copy.deepcopy(a);b[0]['dice']=float('nan')
    with pytest.raises(ValueError):compare_tumor(a,b)
    with pytest.raises(ValueError):paired_cases(a,a+a[:1],'path')


def test_class_regression_blocks_pooled_improvement():
    a=tumor();b=copy.deepcopy(a)
    b[0]['dice']=.47;b[1]['dice']=.9
    assert not compare_tumor(a,b)['checks']['no_class_drop_over_0_02']


def test_stroke_misses_and_false_alarms_both_matter():
    a=[dict(subject='a',reference_voxels=10,dice=.4,absolute_volume_error_ml=3,false_positive_ml=2)]
    b=[dict(a[0],dice=.5,absolute_volume_error_ml=2,false_positive_ml=1)]
    lesions=dict(lesion_recall=.4,lesion_precision=.5,no_overlap_predicted_components=2)
    assert compare_stroke(a,b,lesions,lesions)['development_screen_passed']
    assert not compare_stroke(a,b,lesions,dict(lesions,lesion_recall=.3))['development_screen_passed']
