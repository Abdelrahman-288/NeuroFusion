# Input-quality checks before inference

Implemented 2026-10-06 in `src/neurofusion/input_quality.py`. Every new inference
uses deterministic policy version 1 before model loading. These checks verify
technical properties, not brain anatomy, MRI sequence identity, clinical image
quality, distribution membership or diagnostic suitability.

## Rejections

Tumor-image checks require decodable single-frame PNG/JPEG, at least 32 pixels
per side, at most 4 million pixels, no transparent pixels, and varying grayscale
intensities. Constant images are rejected before loading a model.

DWI checks require decodable 3D NIfTI, positive dimensions, at most 512 voxels per
axis and 16 million total, millimeter spatial units, finite invertible geometry,
finite intensities and finite nonzero-intensity variation. Unsupported tasks and
task-incompatible extensions are rejected. Existing preprocessing checks remain.

## Heuristic warnings

| Input | Warning rule |
|---|---|
| Tumor image | Grayscale 1st–99th percentile range below 10 or standard deviation below 2 |
| Tumor image | More than 5% of pixels have RGB channel spread above 10 |
| Tumor image | Shortest dimension below 128 pixels |
| Tumor image | Longest/shortest dimension ratio above 2 |
| DWI | Largest/smallest affine-derived voxel spacing ratio above 4 |
| DWI | Spacing below 0.2 mm or above 10 mm |
| DWI | Normalized affine-axis dot products differ from an identity matrix by more than 0.01 |
| DWI | Shortest volume dimension below 16 voxels |

These are engineering heuristics, not thresholds established by a clinical study.
Warnings do not block inference or certify an input. Every accepted input retains
a modality-not-verified warning, so the accepted status is
`accepted_with_warnings`. Selecting the correct sequence remains the user's task.
Color content may be an overlay; the system cannot determine its meaning.

## Stored evidence and interface

Successful result JSON includes `input_quality`: policy version, status, metrics,
errors, warnings, scope and `modality_verified: false`. The viewer displays the
status and warnings. Research HTML and JSON exports preserve the checks; older
analyses explicitly say quality was not recorded, with no retrospective claim.

Rejected queued jobs are marked failed with an actionable input-rejection reason.
Their structured quality report is saved under
`experiments/local-viewer/quality/<job>.json`; no prediction result is generated.
Checks run in the background worker before inference, not as a separate browser
preflight or user approval step. Corrupt decoder failures may be reported with a
generic decoding error. No new quality-assessment model is trained in this stage.

## Verification

96 tests pass, including rejection before model loading, low-contrast warning
behavior, color/resolution/aspect warnings, transparency rejection, malformed/4D/
nonfinite/constant/wrong-unit DWI, anisotropic geometry and persisted job errors.
Real development tumor and DWI examples were reprocessed; both probability arrays
matched their earlier saved outputs exactly. Evidence is in
`experiments/input-quality-verification-001/verification.json`.

Regression testing also exposed a review-order tie: entries with equal timestamps
could be ordered by random IDs. Reviews now use SQLite insertion order, with a
same-timestamp regression test. This preserves the order of corrections.

Next milestone: reproducible robustness evaluation on development data using
controlled input perturbations. Calibrated uncertainty, learned out-of-distribution
detection, automatic modality verification and external validation remain pending.
