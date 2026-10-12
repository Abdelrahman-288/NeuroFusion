"""Synthetic fixtures, never clinical data or a model performance benchmark."""
import csv
from pathlib import Path

import nibabel as nib
import numpy as np


def create_demo(root: Path, patients: int = 12) -> Path:
    if root.exists() and any(root.iterdir()):
        raise ValueError("Demo directory must be empty to avoid overwriting data")
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    grid = np.indices((16, 16, 16))
    rows = []
    for i in range(patients):
        subject = f"synthetic-{i:03d}"
        folder = root / subject
        folder.mkdir()
        center = rng.integers(5, 11, size=3)
        mask = (((grid - center[:, None, None, None]) ** 2).sum(axis=0) < 9).astype(np.uint8)
        row = {"subject_id": subject, "study_id": "session-01"}
        for modality in ("dwi", "adc", "flair", "mask"):
            values = mask if modality == "mask" else (rng.normal(size=mask.shape) + mask * 2).astype(np.float32)
            path = folder / f"{modality}.nii.gz"
            nib.save(nib.Nifti1Image(values, np.diag([2., 2., 2., 1.])), path)
            row[modality] = path.relative_to(root).as_posix()
        rows.append(row)
    index = root / "index.csv"
    with index.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return index
