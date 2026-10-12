"""Reversible orientation-only preprocessing for a native-grid DWI baseline.

No registration or spatial resampling is performed. FLAIR fusion needs a separate
registration workflow; matching array sizes alone never implies alignment.
"""
from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.orientations import axcodes2ornt, io_orientation, ornt_transform, apply_orientation

from neurofusion.data import inspect_volume, save_json


def prepare_dwi(image_path: Path, mask_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Choose a new preprocessing output directory")
    image_info = inspect_volume(image_path)
    mask_info = inspect_volume(mask_path, mask=True)
    image, mask = nib.load(image_path), nib.load(mask_path)
    if image.header.get_xyzt_units()[0] != mask.header.get_xyzt_units()[0] or image.shape != mask.shape or not np.allclose(image.affine, mask.affine, rtol=0, atol=1e-4):
        raise ValueError("DWI and mask must share the same physical grid")
    orientation = io_orientation(image.affine)
    transform = ornt_transform(orientation, axcodes2ornt(('R', 'A', 'S')))
    inverse = ornt_transform(axcodes2ornt(('R', 'A', 'S')), orientation)
    canonical = image.as_reoriented(transform)
    values = canonical.get_fdata(dtype=np.float32)
    labels = mask.as_reoriented(transform).get_fdata(dtype=np.float32).astype(np.uint8)
    foreground = values != 0
    selected = values[foreground]
    mean, std = float(selected.mean()), float(selected.std())
    if std < 1e-8:
        raise ValueError("DWI has no usable foreground intensity variation")
    normalized = np.zeros_like(values)
    normalized[foreground] = (selected - mean) / std
    metadata = {"schema_version": 1, "method": "RAS axis permutation/flips + per-image nonzero zscore",
                "original_shape": list(image.shape), "original_affine": image.affine.tolist(),
                "canonical_shape": list(values.shape), "canonical_affine": canonical.affine.tolist(),
                "xyzt_units": list(image.header.get_xyzt_units()),
                "inverse_orientation": inverse.tolist(), "mean": mean, "std": std,
                "dwi_sha256": image_info['sha256'], "mask_sha256": mask_info['sha256'],
                "limitations": "No resampling, skull stripping or anatomical registration. Per-image statistics only."}
    output.mkdir(parents=True)
    normalized_image = nib.Nifti1Image(normalized, canonical.affine)
    label_image = nib.Nifti1Image(labels, canonical.affine)
    for derived in (normalized_image, label_image):
        derived.header.set_xyzt_units(*metadata['xyzt_units'])
    nib.save(normalized_image, output / 'dwi.nii.gz')
    nib.save(label_image, output / 'mask.nii.gz')
    save_json(output / 'transform.json', metadata)
    return metadata


def restore_prediction(prediction: np.ndarray, metadata: dict, output: Path) -> None:
    if output.exists():
        raise ValueError("Prediction output already exists")
    if tuple(prediction.shape) != tuple(metadata['canonical_shape']) or not np.isfinite(prediction).all():
        raise ValueError("Prediction must be finite and match canonical shape")
    restored = apply_orientation(prediction, np.asarray(metadata['inverse_orientation']))
    if tuple(restored.shape) != tuple(metadata['original_shape']):
        raise ValueError("Restored prediction has incorrect shape")
    output.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(restored.astype(np.float32), np.asarray(metadata['original_affine']))
    image.header.set_xyzt_units(*metadata.get('xyzt_units', ['unknown','unknown']))
    nib.save(image, output)
