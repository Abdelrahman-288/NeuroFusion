# Model quality: fixed-budget continuation

Latest stroke follow-up: [zero-overlap regression audit](STROKE_ZERO_OVERLAP.md) rejects threshold 0.65 under strengthened patient-level checks. A fixed correction recovers two new misses but leaves one; the original active model remains unchanged.

Latest tumor follow-up (10 October 2026): [compatibility, uncertainty and qualification checks](TUMOR_QUALIFICATION.md). All three improved segmenters passed compatibility and development uncertainty checks. Classifier calibration failed two checks; independent qualification remains blocked. Mandatory expert review is no longer required; historical gate counts below are superseded by the current release tracker.

The October 9, 2026 experiment continues the existing BRISC tumor and ISLES DWI segmentation checkpoints from epoch 5 to epoch 10. Architecture, learning rate, sampling, splits and threshold remain fixed. The protocol selects epoch 10 before training; intermediate epochs are not substituted after seeing results.

## Verified seed-42 results

| Development metric | Epoch 5 | Epoch 10 |
|---|---:|---:|
| Tumor mean native Dice | 0.6699 | 0.7235 |
| Tumor group-weighted Dice | 0.6644 | 0.7164 |
| Tumor mean false-positive pixels | 1088.35 | 1061.87 |
| Stroke mean native Dice | 0.3607 | 0.3799 |
| Stroke absolute volume error, mL | 9.5529 | 9.8271 |
| Stroke false-positive volume, mL | 8.4738 | 9.0182 |
| Stroke lesion recall | 0.2458 | 0.2824 |
| Stroke lesion precision | 0.2552 | 0.2515 |
| Stroke zero-overlap components per scan | 5.4865 | 6.4595 |

Tumor passes all five prospective relative development checks for seed 42. Stroke passes two of six: volume error, false-positive volume, precision and zero-overlap components regress. The stroke candidate is rejected by this screen despite increased Dice and recall. Its exploratory paired Dice-change interval includes zero (-0.0011 to 0.0397).

All 721 tumor predictions and all 37 stroke volumes were reproduced from final checkpoints and matched saved threshold masks. Coverage verification checks all 10 stroke epochs and 13,920 updates. Lesion analysis uses the pre-existing fixed component matching definition; components are not clinically adjudicated lesions.

## Confirmation and evidence

Additional paired tumor seeds 43 and 44 follow a separate protocol recorded before their results. Each compares its own final epoch 10 with epoch 5; every seed must pass all five checks. Results are published in `experiments/tumor-continuation-confirmation-001/summary.json` when complete, and in the local viewer at `/research/model-quality/index.html`.

Confirmation is complete: all three seeds pass all five checks. Mean Dice changes are 0.6699 to 0.7235 (42), 0.6520 to 0.7141 (43), and 0.6221 to 0.6743 (44). All 721 final predictions were reproduced separately for each seed. This supports repeatability on the same development partition; it does not establish patient-independent generalization. The final epoch was retained even where epoch 9 scored higher.

Primary evidence:

- `experiments/model-quality-001/protocol.json` and `summary.json`
- `experiments/tumor-seg-continuation-001/checkpoint-reproduction.json`
- `experiments/dwi-continuation-002/coverage-verification.json` and `checkpoint-reproduction.json`
- `experiments/lesion-analysis-continuation-001/summary.json`
- `experiments/tumor-continuation-confirmation-001/protocol.json`
- `experiments/model-quality-001/interruption-recovery.json`

Interrupted directories remain intact. Stroke resumed from epoch 9 into a fresh directory; tumor seed 43 resumed from epoch 4 into a fresh epoch-5 directory. Model, optimizer and random state were restored. A narrow safe conversion of NumPy scalar metadata allowed stroke checkpoint loading without unrestricted pickle loading.

## Qualification boundary and remaining work

A follow-up exploratory threshold grid (0.55, 0.65, 0.75) was recorded before evaluation of those thresholds, after observing the original stroke failure. Threshold 0.65 passes all six relative development checks against the epoch-5 baseline: Dice 0.3832, volume error 7.8996 mL, false-positive volume 6.2609 mL, lesion recall 0.2525, precision 0.2676, and 5.0811 zero-overlap components/scan. Thresholds 0.55 and 0.75 fail one check each and are retained. Selection and reporting use `experiments/stroke-threshold-001/protocol.json` and `summary.json`.

This is threshold selection on reused development data, not confirmation. Zero-Dice cases increase from 4 at the epoch-5 baseline to 6 at the selected threshold, despite passing the six predeclared aggregate checks. This un-gated regression must be reviewed before promotion. The original threshold-0.5 result is not overwritten. Independent validation and additional seeded controls remain necessary.

No active model is replaced. No held-out partition or new UCSF qualification case is used for training or inference. BRISC image-similarity groups are not verified patient identities, and tumor segmentation validation contains positive images only. These experiments do not establish screening specificity, independent performance or clinical readiness. Existing UCSF qualification remains 2/10 gates, with 0/20 qualified expert reviews.

The next stroke intervention should address small-lesion misses and confirm the selected threshold across seeded runs with prospectively fixed controls. New architectures or loss/sampling changes require their own protocol, matched controls and verification. Independent evaluation follows a qualified candidate and frozen eligible cohort; software tests cannot replace these steps. Final software regression: 240 tests passed. The selected stroke threshold also passed a separate direct voxel-count recomputation on all 37 saved validation volumes.
