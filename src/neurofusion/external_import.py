"""Manifest-driven external pilot import; explicit IDs, paths and checksums only."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np

from neurofusion.data import save_json
from neurofusion.external_adapter import prepare_pair


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def import_pilot(root, pilot, manifest, output):
    root, output = Path(root).resolve(), Path(output)
    if output.exists():
        raise ValueError('Use a fresh output directory')
    expected = {r['exam_id']: r['patient_id'] for r in pilot['records']}
    if not expected or len(expected) != len(pilot['records']):
        raise ValueError('Pilot must contain unique exam identifiers')
    records = manifest['records']
    seen, paths = set(), set()
    validated = []
    # Validate identity/path declarations before creating any output.
    for row in records:
        exam = row['exam_id']
        if exam in seen or exam not in expected or row['patient_id'] != expected[exam]:
            raise ValueError('Duplicate, unselected exam or patient identity mismatch')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', exam):
            raise ValueError('Unsafe exam identifier')
        seen.add(exam)
        pair = []
        for key in ('image', 'mask'):
            entry = row[key]
            rel = Path(entry['path'])
            path = (root/rel).resolve()
            if rel.is_absolute() or not path.is_relative_to(root) or path in paths:
                raise ValueError('Unsafe or reused source path')
            if not str(path).lower().endswith(('.nii', '.nii.gz')):
                raise ValueError('NIfTI files required')
            if not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
                raise ValueError('Explicit SHA256 required for each source file')
            paths.add(path); pair.append(path)
        if not isinstance(row.get('label_source'), str) or not row['label_source'].strip():
            raise ValueError('Numeric label source reference required')
        validated.append((row, pair))
    output.mkdir(parents=True)
    save_json(output/'pilot.json', pilot)
    save_json(output/'import-manifest.json', manifest)
    results = []
    content_seen = {}
    for row, pair in validated:
        result = {'exam_id': row['exam_id'], 'patient_id': row['patient_id']}
        try:
            hashes = [digest(p) for p in pair]
            for key, actual in zip(('image', 'mask'), hashes):
                if actual != row[key]['sha256']:
                    raise ValueError(f'{key} checksum mismatch')
            if hashes[0] in content_seen:
                raise ValueError('Image content duplicates exam '+content_seen[hashes[0]])
            content_seen[hashes[0]] = row['exam_id']
            images, labels, geometry = prepare_pair(*pair, allowed_labels=row['allowed_labels'])
            # Detect a source being replaced during preparation.
            if [digest(p) for p in pair] != hashes:
                raise ValueError('Source changed during preparation')
            destination = output/row['exam_id']
            destination.mkdir()
            np.savez_compressed(destination/'slices.npz', images=images, numeric_labels=labels)
            geometry['patient_id'] = row['patient_id']
            geometry['exam_id'] = row['exam_id']
            geometry['label_source'] = row['label_source']
            save_json(destination/'geometry.json', geometry)
            result.update(status='prepared_requires_review', slices=len(images),
                          lost_label_slices=len(geometry['lost_label_slices']),
                          archive_sha256=digest(destination/'slices.npz'))
        except (ValueError, OSError, KeyError) as error:
            result.update(status='failed', error=str(error))
        results.append(result)
    for exam in sorted(set(expected)-seen):
        results.append({'exam_id': exam, 'patient_id': expected[exam], 'status': 'awaiting_files'})
    summary = {'pilot_exams': len(expected), 'declared_exams': len(records),
        'prepared': sum(r['status']=='prepared_requires_review' for r in results),
        'failed': sum(r['status']=='failed' for r in results),
        'awaiting_files': sum(r['status']=='awaiting_files' for r in results),
        'evaluation_ready': False, 'model_inference_performed': False,
        'note': 'Prepared arrays still require alignment, label semantics and source-independence review.',
        'results': results}
    save_json(output/'summary.json', summary)
    return summary
