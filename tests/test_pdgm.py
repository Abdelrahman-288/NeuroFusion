import csv
import nibabel as nib
import numpy as np
import pytest

from neurofusion.pdgm import identity, read_metadata, metadata_summary, acquisition_pilot, audit_volume_pair


def write_metadata(path, ids):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['ID', 'Sex', 'WHO CNS Grade', 'BraTS21 ID'])
        for value in ids:
            writer.writerow([value, 'F', '4', ''])


def test_followups_and_padding_share_patient(tmp_path):
    path = tmp_path/'metadata.csv'
    write_metadata(path, ['UCSF-PDGM-433', 'UCSF-PDGM-0433_FU007d', 'UCSF-PDGM-004'])
    rows = read_metadata(path)
    assert rows[0]['patient_id'] == rows[1]['patient_id'] == 'UCSF-PDGM-0433'
    assert metadata_summary(rows)['patients'] == 2
    assert metadata_summary(rows)['followup_exams'] == 1
    pilot = acquisition_pilot(rows)
    assert all(r['followup_days'] is None for r in pilot)
    assert acquisition_pilot(list(reversed(rows))) == pilot
    assert not metadata_summary(rows)['evaluation_ready']


@pytest.mark.parametrize('ids', [[], ['UCSF-PDGM-433', 'UCSF-PDGM-0433'],
                                ['UCSF-PDGM-0433_FU007d'], ['bad-id']])
def test_invalid_identity_metadata_rejected(tmp_path, ids):
    path = tmp_path/'metadata.csv'
    write_metadata(path, ids)
    with pytest.raises(ValueError):
        read_metadata(path)


def make_pair(tmp_path, *, shifted=False, fractional=False, nan=False, units='mm'):
    values = np.arange(120, dtype=np.float32).reshape(4, 5, 6)
    if nan:
        values[1, 1, 1] = np.nan
    target = np.zeros_like(values)
    target[1:3, 1:3, 1:3] = .5 if fractional else 2
    affine = np.diag([-1., 2., 3., 1.])
    paths = []
    for name, array in [('image', values), ('mask', target)]:
        grid = affine.copy()
        if shifted and name == 'mask':
            grid[0, 3] = 1
        volume = nib.Nifti1Image(array, grid)
        volume.header.set_xyzt_units(units)
        path = tmp_path/f'{name}.nii.gz'
        nib.save(volume, path)
        paths.append(path)
    return paths


def test_volume_intake_keeps_native_geometry_and_numeric_labels(tmp_path):
    paths = make_pair(tmp_path)
    report = audit_volume_pair(*paths, allowed_labels=[0, 1, 2, 4])
    assert report['axis_codes'] == ['L', 'A', 'S']
    assert report['spacing_mm'] == [1., 2., 3.]
    assert report['foreground_voxels'] == 8
    assert report['label_voxels']['2'] == 8
    assert not report['label_meanings_verified'] and not report['evaluation_ready']


@pytest.mark.parametrize('options', [{'shifted': True}, {'fractional': True},
                                     {'nan': True}, {'units': 'unknown'}])
def test_invalid_volumes_rejected(tmp_path, options):
    paths = make_pair(tmp_path, **options)
    with pytest.raises(ValueError):
        audit_volume_pair(*paths, allowed_labels=[0, 1, 2, 4])


def test_unexpected_labels_rejected(tmp_path):
    paths = make_pair(tmp_path)
    with pytest.raises(ValueError, match='labels'):
        audit_volume_pair(*paths, allowed_labels=[0, 1])
