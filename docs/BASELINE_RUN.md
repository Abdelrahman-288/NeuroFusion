# First real-data DWI baseline

Updated 2026-10-06. This is a small real-data pipeline check, not a useful medical
model or a full-cohort benchmark. Predictions contain many false positives.

Historical debugging record: the subsequent five-epoch full-cohort run is documented
in `COHORT_TRAINING.md`. The two-case results below are not the latest cohort metrics.

## Data and partitions

The original curated assignments are frozen in
`experiments/isles-curated-001/frozen-splits-v1.json`, bound to the manifest hash.
They contain 174 training, 37 validation and 37 internal holdout subjects.
Two duplicate-content subjects remain quarantined.

The supplied center spreadsheet maps the retained cohort to two centers. Center
counts are 142/32 in training, 26/11 in validation and 28/9 in holdout. Median
reference lesion volumes are approximately 6.92, 5.22 and 10.76 mL. Training has
three empty masks; validation and holdout have none. These mixed-site partitions
are unstratified and have distribution differences. They do not establish
external-site generalization or robust specificity on negative scans.

The pre-fitting design review used descriptive reference-label statistics only.
No holdout predictions or performance have been computed. Source:
`data/downloads/isles-2022-v2.3.1/center_ids.xlsx`; mapping and source hash:
`data/center-map.json`; review: `experiments/split-review-001.json`.

## Implemented training pipeline

- Compact 3D U-Net, 91,417 parameters, channels 8/16/32, GroupNorm, skip connections,
  strided-convolution downsampling and nearest-neighbor upsampling.
- DWI only, canonical RAS orientation, native spacing and nonzero normalization.
- 32-cubed patches; 50% lesion-centered training sampling when lesions exist.
- Adam at 0.001, mixed precision, BCE plus soft Dice, seed 42.
- Full-volume sliding-window validation with overlap 0.5 and fixed threshold 0.5.
- Checkpoints preserve optimizer, scaler, RNG state, data hashes and histories.
- Native-space NIfTI predictions, HTML progress view and selected-slice previews.

The subset runner permits at most 16 training and 4 validation studies in RAM.
It is not the full-cohort loader. Native spacing varies, so physical field of view
has not yet been standardized. Full lesion-level metrics remain pending.

## Recorded runs

Four training studies selected by fixed ID ordering: 0001, 0003, 0004 and 0005.
Validation: 0002 and 0012, with reference masks containing 118 and 56 voxels.
This selection is not representative of the entire cohort.

Current architecture run: `experiments/dwi-baseline-debug-003/`.
After 200 steps, mean validation Dice was 0.00989. The 20-step continuation
`experiments/dwi-baseline-resume-003/` reached mean Dice 0.02074, with 2,603 and
3,050 false-positive voxels in the two validation scans. These are poor results,
not diagnostic accuracy percentages.

The resumed 220-step run exactly matches the uninterrupted control
`experiments/dwi-baseline-control-003/` for parameters, optimizer, scaler, RNG,
loss history and validation metrics. Verification:
`experiments/resume-verification-003.json`. This demonstrates same-environment
continuation, not universal cross-device determinism.

28 automated tests passed for integrity, leakage, transformations, gradients,
empty-mask metrics and sliding-window boundaries. Run 001 is an earlier
nondeterministic architecture; run 002 stopped at an unsupported deterministic
max-pool operation. Both are preserved as historical experiments. Use run 003
with the current architecture.

## Commands for a fresh run

```powershell
cd D:\NeuroFusion
$python = '.\.venv-neurofusion\Scripts\python.exe'
& $python scripts/train_baseline.py --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --output experiments/my-baseline-001 --steps 200
& $python scripts/train_baseline.py --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --output experiments/my-resume-001 --steps 220 --resume experiments/my-baseline-001/last.pt
& $python scripts/preview_predictions.py --run experiments/my-resume-001
```

Use a fresh output directory. Steps are a total target, not additional steps.
`best.pt` is written when the run improves the lineage's validation score; a
continuation without improvement needs its parent's best checkpoint. `last.pt`
is written at the final step. Open `progress.html` and `prediction-preview/index.html`
to inspect the curves and selected failure examples.

## Next gates

The fixed real-patch learning check passed on training subject 0001:
`experiments/real-patch-overfit-001/`. After 1,000 steps, training-patch Dice was
1.0 for 386 lesion voxels and zero false-positive voxels. Loss decreased from
1.75209 to 0.01199. The predeclared gate was Dice >= 0.95 with decreasing loss.
The patch was used for both fitting and scoring, so this is memorization evidence,
not held-out performance. The broader two-case validation result remains poor.

A bounded-memory full-cohort loader and longer schedule have since been implemented
(see `COHORT_TRAINING.md`). Lesion-level metrics remain outstanding. Keep the holdout
unused during development. FLAIR remains excluded until registration is implemented
and tested.
