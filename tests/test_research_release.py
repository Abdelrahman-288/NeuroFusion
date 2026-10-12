import pytest
from neurofusion.research_release import accept_delivery
from neurofusion.cohort import digest


def fixture(tmp_path):
    file=tmp_path/'evidence.json';file.write_text('{}')
    return ([{'id':'model','status':'partial'}],{'model':{'outcome':'delivered_with_limitations','explanation':'Failed qualification; remains restricted'}},
            dict.fromkeys(['regression_tests','installed_package','private_recovery','promotion_rejection','evaluation_disposition'],True),
            [{'path':'evidence.json','sha256':digest(file)}])


def test_delivery_does_not_qualify_models(tmp_path):
    result=accept_delivery(tmp_path,*fixture(tmp_path))
    assert result['delivery_percent']==100
    assert not result['all_models_qualified'] and not result['clinical_ready'] and not result['independent_evaluation_complete']


def test_incomplete_or_changed_evidence_rejects_closure(tmp_path):
    args=fixture(tmp_path)
    args[2]['regression_tests']=False
    with pytest.raises(ValueError):accept_delivery(tmp_path,*args)
    args[2]['regression_tests']=True
    (tmp_path/'evidence.json').write_text('changed')
    with pytest.raises(ValueError):accept_delivery(tmp_path,*args)


def test_missing_requirement_rejects_closure(tmp_path):
    args=fixture(tmp_path);args[1].clear()
    with pytest.raises(ValueError):accept_delivery(tmp_path,*args)
