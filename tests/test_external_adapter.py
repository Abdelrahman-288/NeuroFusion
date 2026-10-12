import nibabel as nib
import numpy as np
import pytest

from neurofusion.external_adapter import prepare_pair, restore_probabilities


def pair(tmp_path, affine=None):
    shape = (16, 24, 8)
    values = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    labels = np.zeros(shape, dtype=np.uint16)
    labels[4:12, 6:18, 2:6] = 2
    if affine is None:
        affine = np.diag([-1., 2., -3., 1.])
    paths = []
    for name, array in [('image', values), ('mask', labels)]:
        image = nib.Nifti1Image(array, affine)
        image.header.set_xyzt_units('mm')
        path = tmp_path/f'{name}.nii.gz'
        nib.save(image, path)
        paths.append(path)
    return paths


def test_all_slices_numeric_labels_and_physical_aspect(tmp_path):
    paths = pair(tmp_path)
    images, labels, meta = prepare_pair(*paths, allowed_labels=[0, 2])
    assert images.shape == (8, 1, 128, 128)
    assert labels.shape == (8, 128, 128)
    assert set(np.unique(labels)) == {0, 2}
    assert meta['resize_wh'] == [43, 128]
    assert meta['slice_indices'] == list(range(8))
    assert not meta['evaluation_ready']
    assert not images[:, :, :, :42].any()


@pytest.mark.parametrize('affine', [np.diag([-1., 2., -3., 1.]),
    np.array([[0,0,3,5],[-1,0,0,6],[0,2,0,7],[0,0,0,1.]])])
def test_reconstruction_handles_flips_and_axis_permutations(tmp_path, affine):
    paths = pair(tmp_path, affine)
    _, _, meta = prepare_pair(*paths, allowed_labels=[0, 2])
    shape = meta['canonical_shape']
    # A unique constant per slice detects reversing the wrong axis during restoration.
    signals = np.linspace(0, 1, shape[2], dtype=np.float32)
    p = np.broadcast_to(signals[:, None, None], (shape[2], 128, 128)).copy()
    restored = restore_probabilities(p, meta)
    expected_canonical = np.broadcast_to(signals, shape)
    transform = nib.orientations.ornt_transform(np.asarray(meta['canonical_orientation']),
                                                np.asarray(meta['native_orientation']))
    expected = nib.orientations.apply_orientation(expected_canonical, transform)
    assert restored.shape == (16, 24, 8)
    assert np.allclose(restored.affine, affine)
    assert np.allclose(restored.get_fdata(), expected, atol=1e-6)
    assert restored.header.get_xyzt_units()[0] == 'mm'


def test_predictions_reject_missing_slices_and_invalid_values(tmp_path):
    _, _, meta = prepare_pair(*pair(tmp_path), allowed_labels=[0, 2])
    for p in [np.zeros((7,128,128)), np.full((8,128,128),np.nan),np.full((8,128,128),1.1)]:
        with pytest.raises(ValueError):
            restore_probabilities(p, meta)


def test_normalization_does_not_use_masks(tmp_path):
    paths = pair(tmp_path)
    first, _, meta = prepare_pair(*paths, allowed_labels=[0, 2])
    mask = nib.load(paths[1])
    nib.save(nib.Nifti1Image(np.zeros(mask.shape,dtype=np.uint16),mask.affine,mask.header), paths[1])
    second, labels, updated = prepare_pair(*paths, allowed_labels=[0, 2])
    assert np.array_equal(first, second) and not labels.any()
    assert meta['intensity'] == updated['intensity']


def test_sheared_grids_require_explicit_resampling(tmp_path):
    affine=np.eye(4);affine[0,1]=.3
    with pytest.raises(ValueError, match='Sheared'):
        prepare_pair(*pair(tmp_path,affine),allowed_labels=[0,2])


def test_label_disappearance_is_reported(tmp_path):
    paths=pair(tmp_path)
    source=nib.load(paths[1])
    labels=np.zeros(source.shape,dtype=np.uint16);labels[1,1,1]=2
    nib.save(nib.Nifti1Image(labels,source.affine,source.header),paths[1])
    _,_,meta=prepare_pair(*paths,allowed_labels=[0,2],size=16)
    assert meta['lost_label_slices']
