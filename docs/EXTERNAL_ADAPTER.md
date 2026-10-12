# External volume adapter: development verification

2026-10-07. The official UCSF-PDGM Aspera package navigation timed out on recheck.
MRI acquisition is still incomplete. This stage implements and verifies import
mechanics using synthetic volumes; it does not score a model or establish clinical
or external-cohort performance. Overall progress remains approximately 80% until
the remaining real-data gates advance.

## Implemented

`src/neurofusion/external_adapter.py` validates an explicit MRI/mask pair using the
existing volume checks, reorders/flips both arrays to canonical RAS axes, and retains
every slice. Whole-volume nonzero 1st/99th percentiles define intensity scaling to
uint8. Segmentation labels never influence normalization or slice inclusion.

Slices are resized to fit a 128 x 128 canvas, preserving in-plane physical aspect
ratio using voxel spacing. Image interpolation is bilinear; label interpolation is
nearest-neighbor. Numeric label IDs are retained without assuming biological meanings
or merging classes. Per-slice disappearance of any foreground label ID is reported.
This does not detect disappearance of every individual lesion when another lesion
with the same numeric label survives.

The output records native and canonical shapes, affines, orientations, slice indices,
intensity range, padding, resized dimensions, source checksums and limitations.
An allocation limit bounds the prepared output; sheared grids are rejected pending
an explicit resampling policy. Oblique but orthogonal grids retain voxel-axis planes,
not true anatomical axial planes. No spatial registration is performed.

`restore_probabilities()` removes padding, resizes full slice coverage to the native
in-plane dimensions, then reverses axis permutations/flips and restores the original
affine and millimeter units. Input must contain finite [0,1] probabilities for every
slice. This restores spatial geometry, not detail lost through resizing.

## Verification

Seven new tests cover physical aspect ratio, numeric labels, all-slice coverage,
native-grid reconstruction under flips and permutations, invalid probabilities,
mask-independent preprocessing, sheared grids and disappearing small labels.
Together with the 11 metadata/intake tests, **18 focused tests passed**.

The final full regression run passed **130 tests** in 34.49 seconds; JUnit evidence
is `experiments/external-adapter-001/tests.xml`. The run initially reproduced the
existing Windows reset on early POST rejection. The HTTP handler now flushes the
error response, sends a write-side shutdown, and drains at most 64 KiB with a short
socket timeout before closing. A 20-request rejection regression test passed with
the complete suite. This fixes the observed failure path without processing rejected
request bodies as application data.

`scripts/verify_external_adapter.py` created a synthetic phantom with a permuted,
flipped, anisotropic affine. Native shape 24 x 32 x 16 became canonical shape
16 x 24 x 32 and 32 model-sized slices. Reconstructing a known synthetic probability
pattern produced maximum absolute error **0.0**, with the native affine restored.
This is not a roundtrip accuracy claim for arbitrary images or model predictions.

Evidence is in `experiments/external-adapter-001/`: HTML report, synthetic preview,
original phantom NIfTIs, slice archive, geometry JSON, restored synthetic probabilities,
summary and source hashes. No patient images or trained models were used.

## Usage

From `D:\NeuroFusion`, use fresh output directories:

```powershell
.venv-neurofusion/Scripts/python.exe scripts/verify_external_adapter.py --output experiments/external-adapter-002
.venv-neurofusion/Scripts/python.exe scripts/prepare_external_slices.py --image experiments/external-adapter-001/image.nii.gz --mask experiments/external-adapter-001/mask.nii.gz --allowed-labels 0 2 --output experiments/external-adapter-cli-001
```

The numeric IDs in this example belong only to the synthetic phantom. For real
data, supply the release's verified label set. `slices.npz` contains `images`
(N,1,128,128 uint8) and `numeric_labels` (N,128,128 uint16). Outputs remain explicitly
marked development-only and not evaluation-ready.

## Remaining gates

- Acquire the documented UCSF import pilot when the official download route works.
- Check real image/mask alignment, orientation and source label meanings.
- Resolve the target mismatch between BRISC binary outlines and UCSF compartments.
- Review normalization/domain shift on pilot patients without using future test patients.
- Reserve separate evaluation patients, verify source relationships, and freeze a
  checkpoint, preprocessing policy, target definition and metrics before scoring.

The adapter is not connected to automatic inference or training. Active models,
BRISC scoring holdout and ISLES scoring holdout are unchanged. See `PDGM_INTAKE.md`.
