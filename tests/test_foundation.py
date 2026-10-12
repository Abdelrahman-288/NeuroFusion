import copy
import csv

import nibabel as nib
import numpy as np
import pytest

from neurofusion.cli import main
from neurofusion.data import audit, build_manifest, inspect_volume, split_patients
from neurofusion.demo import create_demo


@pytest.fixture
def dataset(tmp_path):
    root = tmp_path / "data"
    index = create_demo(root)
    return root, index, build_manifest(index, root, "synthetic-test")


def test_partition_repeatable_and_patient_grouped(dataset):
    _, _, manifest = dataset
    manifest["studies"].append(copy.deepcopy(manifest["studies"][0]))
    manifest["studies"][-1]["study_id"] = "second-session"
    split = split_patients(manifest)
    assert split == split_patients(manifest)
    assert len(split["assignments"]) == 12
    assert audit(manifest, split)["passed"]


def test_duplicate_patient_alias_blocked(dataset):
    _, _, manifest = dataset
    manifest["studies"][1]["files"]["adc"] = copy.deepcopy(manifest["studies"][0]["files"]["dwi"])
    report = audit(manifest, split_patients(manifest))
    assert not report["passed"]
    assert "Duplicate image" in str(report["errors"])


def test_recompressed_copy_detected(dataset):
    root, _, _ = dataset
    source = root / "synthetic-000/dwi.nii.gz"
    dest = root / "copy.nii"
    nib.save(nib.load(source), dest)
    left, right = inspect_volume(source), inspect_volume(dest)
    assert left["sha256"] != right["sha256"]
    assert left["voxel_sha256"] == right["voxel_sha256"]


@pytest.mark.parametrize("problem", ["missing", "extra", "partition", "dataset"])
def test_bad_partitions_blocked(dataset, problem):
    _, _, manifest = dataset
    split = split_patients(manifest)
    if problem == "missing":
        split["assignments"].pop("synthetic-000")
    elif problem == "extra":
        split["assignments"]["unknown"] = "train"
    elif problem == "partition":
        split["assignments"]["synthetic-000"] = "oops"
    else:
        split["dataset_id"] = "wrong"
    assert not audit(manifest, split)["passed"]


@pytest.mark.parametrize("problem", ["nan", "constant", "4d", "mask_values", "mask_geometry"])
def test_bad_images_rejected(dataset, problem):
    root, index, _ = dataset
    key = "mask" if problem.startswith("mask") else "dwi"
    path = root / f"synthetic-000/{key}.nii.gz"
    image = nib.load(path)
    values = image.get_fdata()
    affine = image.affine.copy()
    if problem == "nan":
        values[0, 0, 0] = np.nan
    elif problem == "constant":
        values[:] = 0
    elif problem == "4d":
        values = values[..., None]
    elif problem == "mask_values":
        values[0, 0, 0] = 2
    else:
        affine[0, 3] = 10
    nib.save(nib.Nifti1Image(values, affine), path)
    with pytest.raises(ValueError):
        build_manifest(index, root, "test")


def test_different_flair_geometry_is_flagged(dataset):
    root, index, _ = dataset
    path = root / "synthetic-000/flair.nii.gz"
    image = nib.load(path)
    affine = image.affine.copy()
    affine[0, 3] += 3
    nib.save(nib.Nifti1Image(image.get_fdata(), affine), path)
    manifest = build_manifest(index, root, "test")
    assert "flair" in manifest["studies"][0]["warnings"][0]


def test_outside_dataset_path_rejected(dataset):
    root, index, _ = dataset
    rows = list(csv.DictReader(index.open(newline="")))
    rows[0]["dwi"] = "../outside.nii.gz"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="within the dataset root"):
        build_manifest(index, root, "test")


def test_demo_cli_and_preserve_existing_output(tmp_path):
    output = tmp_path / "demo"
    assert main(["demo", "--output", str(output)]) == 0
    assert (output / "audit.json").exists()
    with pytest.raises(SystemExit) as error:
        main(["demo", "--output", str(output)])
    assert error.value.code == 2


def test_too_few_patients_rejected(dataset):
    _, _, manifest = dataset
    manifest["studies"] = manifest["studies"][:2]
    with pytest.raises(ValueError):
        split_patients(manifest)
