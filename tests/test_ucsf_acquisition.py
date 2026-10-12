import importlib.util
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('ucsf_acquisition',
    Path(__file__).resolve().parents[1]/'scripts/audit_ucsf_acquisition.py')
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


def setup(root, count=2):
    def write(path, text):
        p = root/path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    records = [{'patient_id': f'UCSF-PDGM-{i:04d}', 'exam_id': f'UCSF-PDGM-{i:04d}',
                'files': [f'UCSF-PDGM-{i:04d}_T1c.nii.gz',
                          f'UCSF-PDGM-{i:04d}_tumor_segmentation.nii.gz']}
               for i in range(1, count+1)]
    write('experiments/ucsf-qualification-001/acquisition-queue.json', json.dumps({'records': records}))
    write('data/ucsf-import-manifest.json', '{"records": []}')
    write('data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv',
          'ID,Sex,WHO CNS Grade,BraTS21 ID\n'+''.join(r['exam_id']+',F,4,\n' for r in records))
    write('src/neurofusion/pdgm.py', '# fixture provenance')
    downloads = root/'downloads'
    downloads.mkdir()
    return records, downloads


def pair(downloads, row, *, shifted=False):
    for i, name in enumerate(row['files']):
        values = np.arange(120, dtype=np.float32).reshape(4,5,6) if i == 0 else np.zeros((4,5,6), dtype=np.float32)
        grid = np.eye(4)
        if shifted and i == 1:
            grid[0,3] = 3
        volume = nib.Nifti1Image(values, grid)
        volume.header.set_xyzt_units('mm')
        nib.save(volume, downloads/name)


def test_missing_and_fresh_output_requirement(tmp_path):
    _, downloads = setup(tmp_path)
    out = tmp_path/'out'
    result = intake.run(tmp_path, downloads, out)
    assert result['verified_pairs'] == 0 and result['awaiting_pairs'] == 2
    assert not result['independence_verified'] and not result['model_inference_performed']
    with pytest.raises(ValueError, match='fresh'):
        intake.run(tmp_path, downloads, out)


def test_exact_voxel_duplicate_cannot_count_twice(tmp_path):
    rows, downloads = setup(tmp_path)
    for row in rows:
        pair(downloads, row)
    out = tmp_path/'out'
    result = intake.run(tmp_path, downloads, out)
    assert result['verified_pairs'] == 1 and result['failed_pairs'] == 1
    assert 'duplicate' in result['results'][1]['error']
    assert not (out/'raw'/rows[1]['exam_id']).exists()
    assert all(intake.digest(out/f['path']) == f['sha256'] for f in result['results'][0]['files'])


def test_misaligned_pair_is_not_imported(tmp_path):
    rows, downloads = setup(tmp_path, count=1)
    pair(downloads, rows[0], shifted=True)
    out = tmp_path/'out'
    result = intake.run(tmp_path, downloads, out)
    assert result['verified_pairs'] == 0 and result['failed_pairs'] == 1
    assert not (out/'raw').exists()


def test_known_brats_overlap_stops_before_copy(tmp_path):
    _, downloads = setup(tmp_path, count=1)
    (tmp_path/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv').write_text(
        'ID,Sex,WHO CNS Grade,BraTS21 ID\nUCSF-PDGM-0001,F,4,BraTS2021_00001\n')
    with pytest.raises(ValueError, match='known-overlap'):
        intake.run(tmp_path, downloads, tmp_path/'out')
    assert not (tmp_path/'out').exists()
