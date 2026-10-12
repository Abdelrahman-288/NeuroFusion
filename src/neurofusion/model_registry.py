"""Atomic local model history; evidence-backed promotion and recorded rollback.

Local hashes bind evidence, but do not certify that its scientific claims are true.
Running predictors retain their startup snapshot until restarted.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets

from neurofusion.cohort import digest

GATES = ('development_quality', 'independent_evaluation', 'input_compatibility',
         'uncertainty', 'robustness', 'prediction_reproduction', 'regression_review')


def local_file(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('Expected a project-relative path')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Expected a project-relative path')
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError('Missing file or path outside project')
    return resolved


def bound_file(root, record):
    path = local_file(root, record['path'])
    if digest(path) != record['sha256']:
        raise ValueError('Evidence or checkpoint checksum mismatch')
    return path


def _seal(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def registry_path(root):
    return Path(root) / 'configs/model_registry.json'


def read_registry(root, defaults):
    path = registry_path(root)
    if not path.exists():
        return {'schema_version': 1, 'revisions': []}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or not isinstance(value.get('revisions'), list) or not value['revisions']:
        raise ValueError('Invalid model registry')
    previous = None
    for index, revision in enumerate(value['revisions']):
        payload = {k: v for k, v in revision.items() if k != 'sha256'}
        if revision['sha256'] != _seal(payload) or revision['parent'] != previous:
            raise ValueError('Model registry history changed')
        if revision['number'] != index or set(revision['models']) != set(defaults):
            raise ValueError('Invalid model registry revision')
        if index == 0 and revision['models'] != {k: list(v) for k, v in defaults.items()}:
            raise ValueError('Registry baseline must match pinned models')
        previous = revision['sha256']
    return value


def active_models(root, defaults):
    registry = read_registry(root, defaults)
    models = registry['revisions'][-1]['models'] if registry['revisions'] else defaults
    # Checkpoint hash is checked again immediately before deserialization.
    for relative, checksum in models.values():
        local_file(Path(root), relative)
        if not isinstance(checksum, str) or len(checksum) != 64:
            raise ValueError('Invalid checkpoint hash')
    return {key: tuple(value) for key, value in models.items()}


@contextmanager
def _writer(root):
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    try:
        handle = lock.open('x')
    except FileExistsError:
        raise ValueError('Registry writer already active; inspect stale lock after a crash') from None
    try:
        handle.close()
        yield path
    finally:
        lock.unlink()


def _save(path, value):
    temporary = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(value, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append(value, models, action, evidence=None):
    revisions = value['revisions']
    revision = dict(number=len(revisions), parent=revisions[-1]['sha256'] if revisions else None,
                    models={k: list(v) for k, v in models.items()}, action=action, evidence=evidence)
    revision['sha256'] = _seal(revision)
    revisions.append(revision)
    return revision


def promote(root, defaults, report, expected_revision):
    root = Path(root).resolve()
    with _writer(root) as path:
        value = read_registry(root, defaults)
        current = value['revisions'][-1]['number'] if value['revisions'] else -1
        if current != expected_revision:
            raise ValueError('Registry changed; refresh before promotion')
        report_path = local_file(root, report)
        evidence = json.loads(report_path.read_text(encoding='utf-8'))
        key = evidence.get('model_key')
        if key not in defaults or evidence.get('threshold') != 0.5:
            raise ValueError('Unsupported model key or inference threshold')
        if set(evidence.get('checks', {})) != set(GATES) or any(evidence['checks'][g] is not True for g in GATES):
            raise ValueError('Every required promotion check must pass')
        checkpoint = evidence['checkpoint']
        checkpoint_path = bound_file(root, checkpoint)
        from neurofusion.inference import load_model_checkpoint
        load_model_checkpoint(key, checkpoint_path, checkpoint['sha256'])
        for name in ('protocol', 'training_manifest', 'evaluation'):
            bound_file(root, evidence[name])
        if evidence.get('training_partition') != 'train' or evidence.get('protected_data_used') is not False:
            raise ValueError('Training provenance must exclude protected data')
        # Load the referenced evaluation too; top-level checkboxes alone cannot promote.
        evaluation = json.loads(bound_file(root, evidence['evaluation']).read_text(encoding='utf-8'))
        if (evaluation.get('checkpoint_sha256') != checkpoint['sha256'] or
                evaluation.get('model_key') != key or evaluation.get('checks') != evidence['checks']):
            raise ValueError('Evaluation is not bound to this candidate and its checks')
        from neurofusion.retraining import validate_lineage
        validate_lineage(root,evidence,evaluation)
        models = active_models(root, defaults)
        if not value['revisions']:
            _append(value, defaults, 'pinned_baseline')
        models[key] = (checkpoint['path'], checkpoint['sha256'])
        # Check all files, not only the changed candidate.
        for relative, checksum in models.values():
            bound_file(root, {'path': relative, 'sha256': checksum})
        revision = _append(value, models, 'promote', {'path': report, 'sha256': digest(report_path)})
        _save(path, value)
        return revision


def rollback(root, defaults, target_revision, expected_revision):
    root = Path(root).resolve()
    with _writer(root) as path:
        value = read_registry(root, defaults)
        revisions = value['revisions']
        if not revisions or revisions[-1]['number'] != expected_revision:
            raise ValueError('Registry changed or uninitialized')
        if type(target_revision) is not int or not 0 <= target_revision < expected_revision:
            raise ValueError('Rollback requires an earlier recorded revision')
        models = revisions[target_revision]['models']
        for relative, checksum in models.values():
            bound_file(root, {'path': relative, 'sha256': checksum})
        revision = _append(value, models, 'rollback', {'target_revision': target_revision})
        _save(path, value)
        return revision
