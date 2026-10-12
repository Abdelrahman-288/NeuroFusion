import json
from pathlib import Path

import pytest
import torch

from neurofusion.cohort import digest
from neurofusion.model_registry import GATES, active_models, promote, read_registry, rollback
from neurofusion.tumor_segmentation import TumorUNet


@pytest.fixture
def candidate(tmp_path):
    for name in ('baseline.pt','candidate.pt'):
        torch.save({'model':TumorUNet().state_dict()},tmp_path/name)
    defaults={'tumor_segmenter':('baseline.pt',digest(tmp_path/'baseline.pt'))}
    def binding(name):return {'path':name,'sha256':digest(tmp_path/name)}
    checks=dict.fromkeys(GATES,True)
    (tmp_path/'protocol.json').write_text('{}')
    (tmp_path/'train.json').write_text('{}')
    (tmp_path/'evaluation.json').write_text(json.dumps(dict(model_key='tumor_segmenter',
        checkpoint_sha256=digest(tmp_path/'candidate.pt'),checks=checks)))
    report=dict(model_key='tumor_segmenter',threshold=.5,checks=checks,
        checkpoint=binding('candidate.pt'),protocol=binding('protocol.json'),
        training_manifest=binding('train.json'),evaluation=binding('evaluation.json'),
        training_partition='train',protected_data_used=False)
    # Synthetic lineage exercises integrity controls, not real qualification.
    (tmp_path/'source.json').write_text('{}')
    records=[dict(id=role,partition=role,group=role,image=binding('source.json')) for role in ('train','validation')]
    (tmp_path/'annotations.json').write_text(json.dumps(dict(schema_version=1,model_key='tumor_segmenter',
        protected_data_used=False,source_bindings=[binding('source.json')],records=records)))
    annotation=binding('annotations.json')
    (tmp_path/'protocol.json').write_text(json.dumps(dict(annotation_version=annotation)))
    (tmp_path/'train.json').write_text(json.dumps(dict(annotation_version=annotation,records=records[:1],training_partition='train',protected_data_used=False)))
    (tmp_path/'validation.json').write_text(json.dumps([dict(id='validation',partition='validation',prediction=binding('source.json'))]))
    report.update(schema_version=2,annotation_version=annotation,protocol=binding('protocol.json'),training_manifest=binding('train.json'))
    run={k:report[k] for k in ('model_key','checkpoint','annotation_version','protocol','training_manifest')}
    run.update(validation=binding('validation.json'),checks=checks,missing_evidence=[],protected_data_used=False)
    (tmp_path/'run.json').write_text(json.dumps(run));report['training_run']=binding('run.json')
    (tmp_path/'evaluation.json').write_text(json.dumps(dict(model_key='tumor_segmenter',checkpoint_sha256=report['checkpoint']['sha256'],checks=checks,training_run=report['training_run'])))
    report['evaluation']=binding('evaluation.json')
    (tmp_path/'candidate.json').write_text(json.dumps(report))
    return tmp_path,defaults,report


def test_promotion_rollback_and_stale_writers(candidate):
    root,defaults,report=candidate
    assert active_models(root,defaults)==defaults
    promote(root,defaults,'candidate.json',-1)
    assert active_models(root,defaults)['tumor_segmenter'][0]=='candidate.pt'
    with pytest.raises(ValueError,match='changed'):promote(root,defaults,'candidate.json',-1)
    rollback(root,defaults,0,1)
    assert active_models(root,defaults)==defaults
    assert len(read_registry(root,defaults)['revisions'])==3
    with pytest.raises(ValueError,match='earlier'):rollback(root,defaults,3,2)


@pytest.mark.parametrize('gate',GATES)
def test_any_failed_gate_prevents_promotion(candidate,gate):
    root,defaults,report=candidate
    report['checks'][gate]=False
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='check must pass'):promote(root,defaults,'candidate.json',-1)
    assert not (root/'configs/model_registry.json').exists()


@pytest.mark.parametrize('field',['protocol','training_manifest','evaluation','checkpoint'])
def test_changed_artifact_rejected(candidate,field):
    root,defaults,report=candidate
    (root/report[field]['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):promote(root,defaults,'candidate.json',-1)


def test_protected_training_rejected(candidate):
    root,defaults,report=candidate
    report['protected_data_used']=True
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='protected'):promote(root,defaults,'candidate.json',-1)


def test_lock_and_history_tampering(candidate):
    root,defaults,report=candidate
    (root/'configs').mkdir()
    (root/'configs/model_registry.lock').write_text('')
    with pytest.raises(ValueError,match='writer'):promote(root,defaults,'candidate.json',-1)
    (root/'configs/model_registry.lock').unlink()
    promote(root,defaults,'candidate.json',-1)
    path=root/'configs/model_registry.json'
    registry=json.loads(path.read_text());registry['revisions'][1]['models']['tumor_segmenter'][0]='wrong.pt'
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError,match='history'):active_models(root,defaults)


def test_write_failure_keeps_previous_registry(candidate,monkeypatch):
    root,defaults,report=candidate
    promote(root,defaults,'candidate.json',-1)
    path=root/'configs/model_registry.json';before=path.read_bytes()
    def fail(*args):raise OSError('simulated replace failure')
    monkeypatch.setattr('neurofusion.model_registry.os.replace',fail)
    with pytest.raises(OSError):rollback(root,defaults,0,1)
    assert path.read_bytes()==before
    assert not (root/'configs/model_registry.lock').exists()


def test_evaluation_must_match_candidate(candidate):
    root,defaults,report=candidate
    path=root/'evaluation.json';value=json.loads(path.read_text());value['checkpoint_sha256']='0'*64
    path.write_text(json.dumps(value));report['evaluation']['sha256']=digest(path)
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='bound'):promote(root,defaults,'candidate.json',-1)


def test_path_escape_rejected(candidate):
    root,defaults,report=candidate
    report['checkpoint']['path']='../candidate.pt'
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='relative'):promote(root,defaults,'candidate.json',-1)


def test_running_predictor_retains_snapshot(candidate,monkeypatch):
    from neurofusion.inference import Predictor
    root,defaults,report=candidate
    monkeypatch.setattr('neurofusion.inference.MODELS',defaults)
    running=Predictor(root,'cpu');original=running.model('tumor_segmenter')
    promote(root,defaults,'candidate.json',-1)
    assert running.model('tumor_segmenter') is original
    assert running.registry==defaults
    fresh=Predictor(root,'cpu');fresh.model('tumor_segmenter')
    assert fresh.registry['tumor_segmenter'][0]=='candidate.pt'
    rollback(root,defaults,0,1)
    assert fresh.registry['tumor_segmenter'][0]=='candidate.pt'


def test_nonfinite_checkpoint_rejected(candidate):
    root,defaults,report=candidate
    model=TumorUNet()
    with torch.no_grad():next(model.parameters()).fill_(float('nan'))
    torch.save({'model':model.state_dict()},root/'candidate.pt')
    report['checkpoint']['sha256']=digest(root/'candidate.pt')
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='Nonfinite'):promote(root,defaults,'candidate.json',-1)


def test_promotion_requires_versioned_lineage(candidate):
    root,defaults,report=candidate
    report.pop('schema_version')
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='lineage required'):promote(root,defaults,'candidate.json',-1)
    assert not (root/'configs/model_registry.json').exists()


def test_modified_annotations_reject_promotion(candidate):
    root,defaults,report=candidate
    (root/'annotations.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):promote(root,defaults,'candidate.json',-1)


def test_training_run_cannot_switch_annotation_version(candidate):
    root,defaults,report=candidate
    run=json.loads((root/'run.json').read_text());run['annotation_version']['sha256']='0'*64
    (root/'run.json').write_text(json.dumps(run))
    report['training_run']['sha256']=digest(root/'run.json')
    evaluation=json.loads((root/'evaluation.json').read_text());evaluation['training_run']=report['training_run']
    (root/'evaluation.json').write_text(json.dumps(evaluation));report['evaluation']['sha256']=digest(root/'evaluation.json')
    (root/'candidate.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='lineage binding'):promote(root,defaults,'candidate.json',-1)
