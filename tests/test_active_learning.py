import pytest
from neurofusion.active_learning import select_annotations


def rows():
    return [dict(case_id=f'c{i}',patient_id=f'p{i}',partition='train',role='unlabeled_development',
            patient_identity_verified=True,uncertainty=u,embedding=e,embedding_version='test-v1',
            uncertainty_method='test-only',input_sha256=str(i)*64,model_sha256='f'*64)
        for i,u,e in [(1,.9,[1,0]),(2,.8,[1,0]),(3,.7,[-1,0])]]


def test_diversity_and_deterministic_random_comparator():
    a=select_annotations(rows(),protected_patients=['heldout'],budget=2)
    b=select_annotations(list(reversed(rows())),protected_patients=['heldout'],budget=2)
    assert a==b and [r['case_id'] for r in a['selected']]==['c1','c3']
    assert not a['training_export_permitted'] and not a['benchmark_completed']
    assert all(not r['approved_for_training'] for r in a['selected'])


@pytest.mark.parametrize('change',[{'partition':'test'},{'partition':'validation'},{'role':'heldout'},
 {'patient_identity_verified':False},{'uncertainty':float('nan')},{'embedding':[0,0]},
 {'embedding':[float('inf'),0]},{'model_sha256':'x'},{'embedding_version':'incompatible'}])
def test_ineligible_or_incomparable_pool_rejected(change):
    data=rows();data[0].update(change)
    with pytest.raises(ValueError):select_annotations(data,protected_patients=[],budget=2)


def test_protected_patient_and_repeated_visit_rejected():
    with pytest.raises(ValueError):select_annotations(rows(),protected_patients=['p1'],budget=2)
    data=rows();data[1]['patient_id']='p1'
    with pytest.raises(ValueError):select_annotations(data,protected_patients=[],budget=2)
    with pytest.raises(ValueError):select_annotations(rows(),protected_patients=[],budget=4)


def test_benchmark_initial_pool_patient_separation():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('al_benchmark',Path(__file__).parents[1]/'scripts/benchmark_active_learning.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    records=[{'patient_id':f'p{i}','role':'train' if i<16 else 'development_validation'} for i in range(20)]
    for seed in (42,43,44):
        initial,pool=module.split_train(records,seed)
        assert len(initial)==4 and len(pool)==12
        assert not {r['patient_id'] for r in initial}&{r['patient_id'] for r in pool}
        assert all(r['role']=='train' for r in initial+pool)
        assert module.split_train(list(reversed(records)),seed)==(initial,pool)
