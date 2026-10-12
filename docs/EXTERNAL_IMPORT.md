# External pilot batch importer

2026-10-07. Implemented manifest-driven import using the existing external volume
adapter. No external MRI images have been acquired in this stage. Overall estimated
progress remains 80%; external-image validation and evaluation are incomplete.

## Behavior

`scripts/import_external_pilot.py` requires a source directory, recorded pilot,
explicit file manifest and fresh output directory. Every declared exam must match
the pilot's patient identifier. Duplicate exam IDs, reused paths, path escapes and
non-NIfTI file extensions are rejected before output is created. Each file requires
a SHA256. The importer verifies checksums before preparing slices and again afterward
to detect replacement during processing. It flags identical image-file content
across declared exams; this is not a full decoded-volume or patient overlap audit.

Each successful exam has its own `slices.npz` and `geometry.json`, retaining identity,
source hashes, numeric label source and transformation details. The summary includes
prepared cases, failed cases and selected exams still awaiting files. Failures produce
a nonzero CLI exit status. Prepared cases remain `prepared_requires_review`, and
`evaluation_ready` is always false. A partially written failed exam is not a prepared
case; downstream code must consult the summary rather than count directories.

## Manifest schema

```json
{
  "records": [{
    "exam_id": "UCSF-PDGM-0200",
    "patient_id": "UCSF-PDGM-0200",
    "image": {"path": "relative/path/to/image.nii.gz", "sha256": "64 lowercase hex characters"},
    "mask": {"path": "relative/path/to/mask.nii.gz", "sha256": "64 lowercase hex characters"},
    "allowed_labels": [0, 2],
    "label_source": "Replace with the verified release label documentation"
  }]
}
```

The example numeric labels are placeholders from the synthetic test, not a UCSF
label mapping. Determine the actual allowed labels from the acquired release.
The importer does not guess filenames, infer modalities, or establish label meanings.

From `D:\NeuroFusion`, after acquiring and explicitly mapping real files:

```powershell
.venv-neurofusion/Scripts/python.exe scripts/import_external_pilot.py --root data/raw/ucsf-pdgm-v5 --pilot experiments/pdgm-intake-001/acquisition-pilot.json --manifest data/ucsf-import-manifest.json --output experiments/pdgm-import-001
```

## Evidence

- `experiments/external-import-control-001/`: one synthetic phantom successfully
  prepared end to end. This is not patient data or model inference.
- `experiments/pdgm-import-status-001/`: the actual 20-patient acquisition pilot
  checked with no declared acquired files: **20 awaiting files, 0 prepared**.
- Eight new importer tests cover success/missing distinction, changed checksums,
  invalid identities, duplicate declarations, reused paths and path escapes.
- All 26 focused importer, adapter and metadata tests passed.
- Full regression suite: **138 passed** in 56.40 seconds. JUnit evidence: `experiments/external-import-control-001/tests.xml`.

Next: acquire pilot scans through the official source, populate the checksummed
manifest, run this importer and review real alignment and label semantics. Then
define a compatible target and freeze a separate evaluation cohort/protocol.
See `PDGM_INTAKE.md` and `EXTERNAL_ADAPTER.md`.
