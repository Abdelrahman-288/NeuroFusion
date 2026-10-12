import numpy as np
import pytest
from neurofusion.specialist_plan import engineering_partition,numeric_foreground


def test_partition_order_invariance_and_followup_grouping():
    rows=[{'exam_id':f'e{i}','patient_id':f'p{i//2}'} for i in range(8)]
    a=engineering_partition(rows,2);b=engineering_partition(rows[::-1],2)
    assert a==b and not set(a['train_patients'])&set(a['development_validation_patients'])
    for patient in ['p0','p1','p2','p3']:
        assert len({r['role'] for r in a['records'] if r['patient_id']==patient})==1
    assert a['test_patients']==0 and not a['external_evaluation_ready']


def test_union_preserves_empty_slices():
    mask=np.zeros((2,2,3));mask[0,0,0]=1;mask[0,1,0]=2;mask[1,0,0]=4
    result=numeric_foreground(mask)
    assert result.shape==mask.shape and result.sum()==3 and not result[:,:,1:].any()


@pytest.mark.parametrize('bad',[3,.5,np.nan,-1])
def test_unknown_labels_rejected(bad):
    with pytest.raises(ValueError):numeric_foreground(np.full((2,2,2),bad))


def test_invalid_partition_rejected():
    with pytest.raises(ValueError):engineering_partition([{'exam_id':'a','patient_id':'p'}],1)
    with pytest.raises(ValueError):engineering_partition([{'exam_id':'a','patient_id':'p'},{'exam_id':'a','patient_id':'q'}],1)
