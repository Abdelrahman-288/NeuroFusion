import pytest
from neurofusion.qualification import acquisition_queue,qualification_gates


def row(i,**kw):return dict(patient_id=str(i),baseline_exam_id=str(i),candidate=True,brats21_ids=[],exclusion_reasons=[],development_patient=False,**kw)


def test_queue_is_patient_disjoint_and_deterministic():
    rows=[row(i) for i in range(8)];rows[1]['brats21_ids']=['mapped'];rows[2]['development_patient']=True
    a=acquisition_queue({'patients':rows},{'0'},3)
    b=acquisition_queue({'patients':list(reversed(rows))},{'0'},3)
    assert a==b and a['eligible_patients']==5
    assert not {'0','1','2'} & {r['patient_id'] for r in a['records']}
    assert not a['cohort_frozen'] and not a['independence_verified']
    with pytest.raises(ValueError):acquisition_queue({'patients':rows+[rows[0]]},set(),1)
    with pytest.raises(ValueError):acquisition_queue({'patients':rows},set(),99)


def test_qualification_fails_closed_and_does_not_accept_truthy_strings():
    assert qualification_gates({})['passed']==0
    e={'reproducibility_verified':True,'all_seeds_passed':'true','independence_verified':True}
    q=qualification_gates(e)
    assert q['passed']==2 and not q['qualified_for_research_release'] and not q['clinical_ready']


def test_expert_review_optional_without_waiving_other_gates():
    result=qualification_gates({'expert_review_complete':True})
    assert result['total']==9 and result['passed']==0
    assert 'expert_alignment_review' not in {g['id'] for g in result['gates']}
    assert qualification_gates({},require_expert_review=True)['total']==10
    assert not result['qualified_for_research_release'] and not result['clinical_ready']
