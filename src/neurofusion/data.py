"""Explicit study indexing, NIfTI quality control and leakage auditing."""
from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

import nibabel as nib
import numpy as np

MODALITIES = ("dwi", "adc", "flair")
PARTITIONS = ("train", "validation", "holdout")


def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def inspect_volume(path: Path, *, mask: bool = False) -> dict:
    try:
        image = nib.load(path)
    except nib.filebasedimages.ImageFileError as exc:
        raise ValueError(f"Unreadable NIfTI image: {path.name}") from exc
    if len(image.shape) != 3 or min(image.shape) < 2:
        raise ValueError(f"Expected a nonempty 3D volume: {path.name}")
    affine = np.asarray(image.affine, dtype=np.float64)
    if not all(np.isfinite(s) and s > 0 for s in image.header.get_zooms()):
        raise ValueError(f"Invalid voxel spacing: {path.name}")
    if not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3, :3])) < 1e-10:
        raise ValueError(f"Invalid spatial affine: {path.name}")
    voxels = image.get_fdata(dtype=np.float32)
    if not np.isfinite(voxels).all():
        raise ValueError(f"Nonfinite voxel values: {path.name}")
    if mask:
        if not np.isin(voxels, [0, 1]).all():
            raise ValueError(f"Expected binary lesion mask: {path.name}")
    elif float(voxels.max()) == float(voxels.min()):
        raise ValueError(f"Constant image: {path.name}")
    file_hash = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            file_hash.update(block)
    # Decoded-data fingerprint also detects recompressed copies. This is an
    # exact-copy check, not a substitute for patient identity or near-duplicate QC.
    content_hash = hashlib.sha256()
    content_hash.update(str(voxels.shape).encode())
    content_hash.update(np.ascontiguousarray(voxels, dtype="<f4").tobytes())
    unit = image.header.get_xyzt_units()[0]
    mm_scale = {'mm': 1., 'meter': 1000., 'micron': .001}.get(unit)
    result = {
        "shape": list(image.shape), "spatial_units": unit,
        "spacing": list(map(float, image.header.get_zooms())),
        "spacing_mm": [float(s)*mm_scale for s in image.header.get_zooms()] if mm_scale is not None else None,
        "affine": affine.tolist(), "orientation": list(nib.aff2axcodes(affine)),
        "sha256": file_hash.hexdigest(), "voxel_sha256": content_hash.hexdigest(),
    }
    if mask:
        result["lesion_voxels"] = int(np.count_nonzero(voxels))
        result["lesion_volume_ml"] = (float(np.count_nonzero(voxels) * abs(np.linalg.det(affine[:3, :3])) * mm_scale**3 / 1000)
                                      if mm_scale is not None else None)
    return result


def build_manifest(index: Path, root: Path, dataset_id: str) -> dict:
    root = root.resolve()
    if not dataset_id.strip():
        raise ValueError("dataset_id is required")
    with index.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"subject_id", "study_id", *MODALITIES, "mask"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain: {', '.join(sorted(required))}")
        rows = list(reader)
    if not rows:
        raise ValueError("Index is empty")
    studies, seen = [], set()
    for row in rows:
        subject, study = row["subject_id"].strip(), row["study_id"].strip()
        if not subject or not study or (subject, study) in seen:
            raise ValueError("Missing identity or repeated subject/study pair")
        seen.add((subject, study))
        files = {}
        for key in (*MODALITIES, "mask"):
            if not row[key].strip():
                raise ValueError(f"Missing {key} for {subject}/{study}")
            path = (root / row[key]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Indexed paths must remain within the dataset root")
            files[key] = {"path": path.relative_to(root).as_posix(), **inspect_volume(path, mask=key == "mask")}
        warnings = []
        for key in ("adc", "flair", "mask"):
            aligned = files[key]["spatial_units"] == files["dwi"]["spatial_units"] and files[key]["shape"] == files["dwi"]["shape"] and np.allclose(
                files[key]["affine"], files["dwi"]["affine"], atol=1e-4, rtol=0)
            if not aligned:
                if key == "mask":
                    raise ValueError(f"Mask must match DWI geometry: {subject}/{study}")
                warnings.append(f"{key}: geometry differs from DWI; registration/resampling review required before fusion")
        studies.append({"subject_id": subject, "study_id": study, "files": files, "warnings": warnings})
    return {"schema_version": 1, "dataset_id": dataset_id, "data_root": str(root),
            "studies": sorted(studies, key=lambda s: (s["subject_id"], s["study_id"]))}


def split_patients(manifest: dict, seed: int = 42) -> dict:
    subjects = sorted({s["subject_id"] for s in manifest["studies"]})
    if len(subjects) < 3:
        raise ValueError("At least 3 patients are needed for three nonempty partitions")
    random.Random(seed).shuffle(subjects)
    n_val = max(1, int(len(subjects) * .15))
    n_test = max(1, int(len(subjects) * .15))
    n_train = len(subjects) - n_val - n_test
    assignments = {p: "train" if i < n_train else "validation" if i < n_train + n_val else "holdout"
                   for i, p in enumerate(subjects)}
    return {"schema_version": 1, "dataset_id": manifest["dataset_id"], "seed": seed,
            "method": "patient_random_approximately_70_15_15; not site/lesion stratified",
            "holdout_note": "Internal development holdout, not official challenge test data",
            "assignments": assignments}


def audit(manifest: dict, splits: dict) -> dict:
    errors, warnings = [], []
    subjects = {s["subject_id"] for s in manifest["studies"]}
    assignments = splits.get("assignments", {})
    if manifest["dataset_id"] != splits.get("dataset_id"):
        errors.append("Dataset identity mismatch")
    if subjects != set(assignments):
        errors.append("Assignments must cover exactly the manifest patients")
    if set(assignments.values()) != set(PARTITIONS):
        errors.append("Expected nonempty train, validation and holdout partitions only")
    seen = {}
    for study in manifest["studies"]:
        subject = study["subject_id"]
        warnings.extend(f"{subject}/{study['study_id']}: {w}" for w in study.get("warnings", []))
        for modality in MODALITIES:
            signature = study["files"][modality]["voxel_sha256"]
            for other_subject in seen.get(signature, set()):
                if subject != other_subject:
                    errors.append(f"Duplicate image content under different patients: {other_subject}, {subject}")
            seen.setdefault(signature, set()).add(subject)
    return {"passed": not errors, "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "patient_counts": {p: sum(v == p for v in assignments.values()) for p in PARTITIONS},
            "limitations": ["Exact voxel copies and supplied identities only; near duplicates and unknown patient aliases require review.",
                            "Geometry checks do not prove anatomical registration or image quality.",
                            "Hashes describe manifest-build time; rebuild after any data changes."]}
