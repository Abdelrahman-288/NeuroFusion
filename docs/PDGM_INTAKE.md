# UCSF-PDGM metadata acquisition and volume intake

Stage date: 2026-10-07. Metadata acquisition and patient indexing are complete.
MRI acquisition is incomplete: the official Aspera package page returned
"temporarily unavailable" in the browser, and TCIA displayed a maintenance notice.
No external MRI scans were downloaded, used for training or scored in this stage.

## Downloaded and verified locally

The official [TCIA collection](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/)
links the v5 clinical metadata and glossary. We saved both original files and a
source-page snapshot in `data/downloads/ucsf-pdgm-v5-metadata/`, with retrieval
time, URLs, sizes and SHA256 values in `provenance.json`. These are local acquisition
hashes, not publisher checksums. The intake script verifies them before parsing.
The glossary is retained as original bytes (it is not UTF-8); it is not an input
to the automated parser.

The observed D: drive had approximately 505 GiB free. The source lists a 142 GB
Aspera image package; space is not the current blocker. No software was installed
and no background image transfer is running.

## Measured metadata results

| Item | Count |
|---|---:|
| Exam records | 501 |
| Unique patients | 495 |
| Follow-up exams grouped with baseline | 6 |
| Exams with BraTS 2021 mapping | 298 |
| Patients with BraTS 2021 mapping | 296 |
| Baseline grade 2 / 3 / 4 | 56 / 43 / 396 |
| MRI volumes acquired | 0 |

Three- and four-digit IDs normalize to the same four-digit patient key. Source
IDs remain preserved. Follow-up suffixes are parsed according to the publisher's
documented corrections; every follow-up must have a baseline. Duplicate normalized
exam IDs and inconsistent sex within a patient are rejected. These checks do not
prove independence from BRISC, whose patient identifiers remain unavailable.

`experiments/pdgm-intake-001/` contains the summary, patient index, acquisition
provenance and a 20-patient import pilot. Pilot selection sorts baseline patient
IDs by SHA256 with a fixed prefix. It does not use grade, outcomes or predictions.
The pilot is for developing import checks, **not a frozen evaluation cohort**.
An eventual evaluation should reserve separate patients and document that choice
before scoring. This dataset contains diffuse glioma cases, not all four BRISC
classes and not a general brain-screening population.

## Implemented volume checks

`src/neurofusion/pdgm.py` and `scripts/audit_external_volume.py` inspect an explicit
MRI/segmentation pair. They require bounded 3D arrays, explicit millimeter units,
finite nonsingular affine matrices, matching grids, finite voxel values, nonconstant
images and integer labels drawn from an explicit permitted set. They retain native
orientation and do not silently resample, normalize or infer label meanings.

The new checks passed synthetic tests with anisotropic and flipped native axes,
and reject shifted masks, fractional labels, NaNs, unknown units and unexpected
labels. Real UCSF volume validation remains pending. The full model-input adapter,
label mapping and evaluation protocol are still to be implemented and verified.
Do not equate BRISC's binary outlines with UCSF's tumor compartments without a
documented, defensible target definition.

Validation: all 11 new metadata/volume tests passed. The full 122-test run had
121 passes and one Windows `ConnectionAbortedError` in an existing API rejection
test. All six API tests passed on the targeted rerun, including the new report
route and path restrictions. The intermittent socket failure remains a known
test/runtime limitation; no external MRI validation is claimed.
Subsequent adapter stage: the observed early-rejection socket reset was fixed and
the expanded 130-test suite passed. See `EXTERNAL_ADAPTER.md` for current evidence.

## Commands

Run from `D:\NeuroFusion`. Use fresh output paths when repeating acquisition or intake.

```powershell
.venv-neurofusion/Scripts/python.exe scripts/download_pdgm_metadata.py
.venv-neurofusion/Scripts/python.exe scripts/prepare_pdgm_intake.py --output experiments/pdgm-intake-002
.venv-neurofusion/Scripts/python.exe -m pytest tests/test_pdgm.py -q
```

When source volumes arrive, the audit CLI takes `--image`, `--mask`,
`--allowed-labels` and `--output`. Supply the numeric label set verified from that
release; passing the audit does not certify label semantics or evaluation readiness.

## Next stage and remaining gates

1. Recheck the official download service and acquire the documented pilot's
   postcontrast T1 and segmentation files where selective download is available.
2. Record the exact package/version, file checksums and source-to-local ID mapping.
3. Run the intake checks on real volumes and review representative image/mask alignment.
4. Define a compatible segmentation target and implement a tested preprocessing adapter.
5. Verify source relationships, reserve an evaluation cohort, and freeze preprocessing,
   selected checkpoint and metrics before model scoring.

The active viewer models and frozen BRISC/ISLES model-scoring holdouts are unchanged.
No independent performance result exists yet.

## Attribution

Calabrese, E., Villanueva-Meyer, J., Rudie, J., Rauschecker, A., Baid, U., Bakas, S.,
Cha, S., Mongan, J., Hess, C. (2022). The University of California San Francisco
Preoperative Diffuse Glioma MRI (UCSF-PDGM), Version 5. The Cancer Imaging Archive.
https://doi.org/10.7937/tcia.bdgf-8v37. Source license: CC BY 4.0. Original CSVs are
unchanged; normalized identifiers, grouping and pilot selection are our derived data.
