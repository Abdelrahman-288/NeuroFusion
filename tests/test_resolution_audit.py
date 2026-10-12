import numpy as np
import pytest
from neurofusion.resolution_audit import compare_masks, restore_categorical


def test_detects_small_component_loss_even_when_label_survives():
    native = np.zeros((8, 8, 8), dtype=np.uint16)
    native[0, 0, 0] = 2
    native[4:7, 4:7, 4:7] = 2
    restored = native.copy()
    restored[0, 0, 0] = 0
    row = compare_masks(native, restored)[0]
    assert row['native_components_26'] == 2
    assert row['missing_component_sizes_voxels'] == [1]
    assert row['roundtrip_dice'] == pytest.approx(54/55)


def test_identity_with_transpose_and_padding():
    native = np.zeros((4, 6, 2), dtype=np.uint16)
    native[1:3, 2:5, 1] = 4
    prepared = np.zeros((2, 8, 8), dtype=np.uint16)
    prepared[:, 1:7, 2:6] = native.transpose(2, 1, 0)
    meta = dict(canonical_shape=[4,6,2], size=8, resize_wh=[4,6], offset_xy=[2,1])
    result = restore_categorical(prepared, meta)
    assert np.array_equal(native, result)
    assert compare_masks(native, result)[0]['roundtrip_dice'] == 1


@pytest.mark.parametrize('bad', [np.nan, -1, .5])
def test_reject_invalid_labels(bad):
    a = np.zeros((2,2,2)); a[0,0,0] = bad
    with pytest.raises(ValueError):
        compare_masks(a, np.zeros_like(a))


def test_empty_foreground_and_unexpected_output_label():
    a = np.zeros((2,2,2), dtype=np.uint16)
    assert compare_masks(a,a) == []
    b=a.copy(); b[0,0,0]=4
    assert compare_masks(a,b)[0]['roundtrip_dice'] == 0
