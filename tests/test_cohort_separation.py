import pytest
from neurofusion.cohort_separation import audit_separation


def row(patient, exam, days=None, mapping=None):
    return dict(patient_id=patient, exam_id=exam, followup_days=days, brats21_id=mapping)


def test_development_followup_excludes_whole_patient():
    result=audit_separation([row('a','a'),row('a','a-followup',12),row('b','b')],['a-followup'])
    assert result['development_patient_exams_excluded']==2
    assert [p['patient_id'] for p in result['patients'] if p['candidate']]==['b']
    assert not result['evaluation_ready'] and not result['cohort_frozen']


def test_mapping_on_followup_excludes_baseline_too():
    r=audit_separation([row('a','a'),row('b','b'),row('b','b-fu',2,'BraTS2021_00001'),row('c','c')],['a'])
    assert r['candidate_patients']==1
    assert r['patients'][1]['brats21_ids']==['BraTS2021_00001']
    assert not r['patients'][2]['independence_verified']


@pytest.mark.parametrize('records,ids', [([row('a','a')],['unknown']),
    ([row('a','a'),row('b','a')],['a']),([row('a','a'),row('a','a2')],['a'])])
def test_invalid_identity_is_rejected(records,ids):
    with pytest.raises(ValueError): audit_separation(records,ids)
