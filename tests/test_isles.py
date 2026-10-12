import pytest
from neurofusion.isles import index_isles


def files(root):
    for suffix in ['dwi','adc','FLAIR','msk']:
        folder = root / ('derivatives' if suffix == 'msk' else 'raw')
        folder.mkdir(exist_ok=True)
        (folder/f'sub-strokecase0001_ses-0001_{suffix}.nii.gz').touch()


def test_bids_index(tmp_path):
    files(tmp_path)
    assert index_isles(tmp_path,tmp_path/'index.csv') == 1
    assert 'sub-strokecase0001,ses-0001' in (tmp_path/'index.csv').read_text()


def test_duplicate_sequence_rejected(tmp_path):
    files(tmp_path)
    (tmp_path/'sub-strokecase0001_ses-0001_run-2_dwi.nii.gz').touch()
    with pytest.raises(ValueError,match='Ambiguous'):
        index_isles(tmp_path,tmp_path/'index.csv')


def test_missing_sequence_rejected(tmp_path):
    (tmp_path/'sub-strokecase0001_ses-0001_dwi.nii.gz').touch()
    with pytest.raises(ValueError,match='Missing'):
        index_isles(tmp_path,tmp_path/'index.csv')
