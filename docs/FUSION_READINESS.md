# DWI + ADC fusion readiness

Completed 2026-10-06. This is the input-pipeline milestone; full fusion training
and validation are next.

All 211 development studies (174 training, 37 validation) passed ADC source-hash,
finite-intensity, nonconstant-intensity, physical-grid and spatial-unit checks.
No holdout volumes were loaded. Source data was not modified or resampled.

DWI and ADC are independently normalized and stacked in a fixed channel order.
Patch sampling crops both channels at identical coordinates. The two-channel
Compact 3D U-Net has 91,633 parameters. Five GPU optimization steps on one training
patch passed, with loss 1.8797 to 1.5354. This is a pipeline check, not a fusion
generalization result. All 45 project tests passed.

Paired training-slice previews and the audit are in `experiments/fusion-readiness-001/`.
Equal grids do not prove anatomical alignment; selected previews do not replace
full-volume expert review. FLAIR remains excluded because its geometry differs.
Additional datasets and tumor/CT specialists remain planned.

## Next fusion experiment

The runner accepts `--inputs dwi-adc`; default DWI behavior is preserved.
Resume checking prevents continuing a DWI checkpoint as a two-channel model.
Use a fresh output folder:

```powershell
Set-Location D:\NeuroFusion
& .\.venv-neurofusion\Scripts\python.exe scripts/train_cohort.py --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache --output experiments/dwi-adc-001 --epochs 5 --patches-per-study 8 --sampling component --inputs dwi-adc
```

Compare final-epoch Dice, lesion recall by size and false positives against
`dwi-component-001`. Two-channel initialization differs because the first layer
has a new shape. The sampling-only comparison script intentionally rejects this
comparison; a fusion-aware comparison must allow architecture/input changes.
Full fusion training subsequently completed in `dwi-adc-002`; see
`FUSION_EXPERIMENT.md` for results and the decision to retain the DWI baseline.
