"""Fail closed before starting cohort QA on mismatched or changed inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('problem', ['checksum', 'escape', 'incomplete'])
def test_invalid_pilot_does_not_create_output(tmp_path, problem):
    root = tmp_path/'data'; root.mkdir()
    source = root/'scan.nii.gz'; source.write_bytes(b'fixture')
    record = {'exam_id': 'exam-1'}
    for role in ('image', 'mask'):
        record[role] = {'path': source.name,
                        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    if problem == 'checksum':
        record['image']['sha256'] = '0'*64
    if problem == 'escape':
        record['image']['path'] = '../outside.nii.gz'
    imported = tmp_path/'import'; imported.mkdir()
    (imported/'import-manifest.json').write_text(json.dumps({'records': [record]}))
    (imported/'summary.json').write_text(json.dumps({'failed': 0,
        'awaiting_files': int(problem == 'incomplete'), 'results': [
            {'exam_id': 'exam-1', 'status': 'prepared_requires_review'}]}))
    output = tmp_path/'output'
    script = Path(__file__).resolve().parents[1]/'scripts/audit_pdgm_pilot_resolution.py'
    result = subprocess.run([sys.executable, str(script), '--root', str(root),
        '--import-dir', str(imported), '--output', str(output)], capture_output=True, text=True)
    assert result.returncode != 0
    assert not output.exists()
    assert {'checksum':'checksum mismatch', 'escape':'escapes dataset root',
            'incomplete':'Complete the pilot import'}[problem] in result.stderr
