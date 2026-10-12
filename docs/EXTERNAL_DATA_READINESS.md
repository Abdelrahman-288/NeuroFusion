# External evaluation readiness and overlap audit

Completed tooling/source-review stage: 2026-10-07. No new external cohort has been
downloaded or scored. No checkpoint was promoted. Both frozen holdouts remain
unused for model scoring; BRISC test image content is included only in leakage auditing.

## Source review

The [BRISC paper](https://www.nature.com/articles/s41597-026-06753-y), Data Records,
explicitly derives BRISC from Nickparvar's Brain Tumor MRI Dataset and identifies
Cheng, SARTAJ and Br35H as its upstream sources. These collections are not independent
test sets by default. Removing exact duplicates alone cannot establish independent
patients, especially when the original patient identifiers are unavailable.

[UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/) is a candidate
for a glioma-specific study: the current TCIA release lists 495 patients and 501
exams, including follow-ups, with MRI and annotations under CC BY 4.0. Its metadata
includes a BraTS mapping to help prevent shared-patient leakage. Its 3D volumes need
an adapter and a frozen task-specific protocol; a glioma-only cohort cannot validate
four-class accuracy. Independence from our training sources still needs review.
The listed image download is about 142 GB and uses Aspera; no bulk acquisition was
started in this stage. Source facts were checked on 2026-10-07.

Machine-readable decisions: `configs/external_dataset_readiness.json`. These entries
are candidates, not additions to the downloaded-dataset registry.

## Implemented auditor

`src/neurofusion/overlap.py` computes file SHA256, decoded RGB pixel SHA256 and the
same 63-bit low-frequency DCT hash used by the existing BRISC audit. Hamming distance
at most four marks a similarity review candidate. Exact overlap takes precedence.
All images belonging to a flagged candidate patient are held for review. Unknown
patient IDs remain unknown; filenames are never converted into patient IDs.

The CLI verifies every reference image against frozen split checksums, reads all
6,000 reference classification images, rejects path escapes/duplicate entries,
and stores candidate and reference fingerprints, match evidence and source hashes.
It performs no model inference. PNG/JPEG only; it does not yet audit 3D volumes.
Cropping, rotation, neighboring slices and scanner changes may evade this screen.
Zero matches never automatically establishes readiness or patient independence.

Candidate manifest example (use real source metadata, not guessed patient IDs):

```json
{
  "dataset_id": "versioned-cohort-id",
  "source": "publisher URL and version",
  "license": "reviewed source terms",
  "purpose": "proposed external task",
  "images": [{"path": "images/example.png", "patient_id": null}]
}
```

An optional `sha256` on each image is verified if supplied. The generated report
records hashes even when the input manifest has none.

Run from `D:\NeuroFusion` in PowerShell:

```powershell
.venv-neurofusion/Scripts/python.exe scripts/audit_external_overlap.py --candidate-root data/external/example --manifest data/external/example/manifest.json --output experiments/external-example-001
```

Use a fresh output directory every time. Do not merge external evaluation data into
training or select checkpoints using its results.

## Verification on real BRISC controls

`scripts/prepare_overlap_control.py` selected one frozen training image per class,
made a file copy, lossless decoded PNG and resized PNG of each, then added one
synthetic image with a mock control patient ID. These are deliberately overlapping
controls, not new patients. All 13 were screened against all 6,000 BRISC images:

| Check | Result |
|---|---:|
| Exact-copy/decoded-copy controls detected | 8 / 8 |
| Resized controls flagged for similarity review | 4 / 4 |
| Additional control held through mock patient ID | 1 / 1 |
| Independent evaluation ready | No |

Evidence: `experiments/external-overlap-001/index.html`, `summary.json`,
`fingerprints.json`, `candidate-manifest.json`, `provenance.json`.
The viewer exposes only the HTML report and summary at `/research/overlap/`.
Unit tests cover re-encoding, threshold boundaries, patient propagation,
missing IDs, non-certification with zero matches, unsafe paths and changed files.
Full regression suite: **111 passed** on 2026-10-07 (32.66 seconds).

## Next stage

Acquire a suitable versioned external cohort or a documented subset; verify patient
grouping and source relationships; implement its volume/label adapter; freeze the
cohort, preprocessing and checkpoint before any scoring. For UCSF-PDGM, select a
glioma segmentation/domain-shift question rather than four-class classification.
Four-class external validation remains an open data requirement. This stage added
readiness infrastructure; it did not improve measured model accuracy.
