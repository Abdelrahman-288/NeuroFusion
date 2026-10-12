# UCSF specialist refinement — 10 October 2026

**Fixed three-seed training and evaluation completed. No active model changed.**

Each stabilized, clipped epoch-5 model received five additional epochs at learning rate 0.0003 with a reset Adam optimizer. The architecture, loss, threshold 0.5, uniform training-slice sampling, clipping norm 1 and AMP remain unchanged. Only the final epoch was eligible; no best-epoch selection was used.

The same 16 training and four development-validation patients were used. The separately acquired protected 20-patient cohort was not used. No data was downloaded.

## New comparison against stabilized controls

This is an explicitly new experiment, not a reinterpretation of the original failed clipping comparison. All four prior relative checks plus no newly zero-Dice patient must pass in every seed.

| Seed | Control Dice | Refined Dice | Control FP mL | Refined FP mL | Checks |
| --- | --- | --- | --- | --- | --- |
| 42 | 0.46169 | 0.53664 | 5.793 | 22.352 | 4/5 |
| 43 | 0.49310 | 0.44035 | 26.018 | 11.776 | 2/5 |
| 44 | 0.43985 | 0.47584 | 25.412 | 14.680 | 5/5 |

**Decision: reject refinement; retain current models.**

- Seed 42: mean_false_positive_volume_not_higher failed.
- Seed 43: mean_dice_increases, mean_iou_not_lower, no_patient_dice_drop_over_005 failed.
- Seed 44: all new development checks passed.

## Original qualification remains separate

Comparing these new candidates against the original unclipped controls: all seeds pass the original four checks = **False**. Full details are retained in `original-control-comparison.json`. The original seed-43 control predicts no foreground and has zero false positives. Improving its overlap does not automatically satisfy its zero-FP comparison. That failed rule is not silently relaxed.

Four repeatedly inspected patients cannot establish generalization. Passing a new development comparison would not itself satisfy target-contract, independence, uncertainty or independent-performance requirements. No result is labeled clinical qualification.

## Verification

- All 15 checkpoint epochs, protocol bindings and actual optimizer learning rates checked.
- All 12 final patient masks and metric dictionaries reproduced after reloading checkpoints.
- All 2,480 training slices covered in every refinement epoch.
- Source and cache checksums and frozen patient roles checked.
- Original and new comparison decisions retained; no promotion performed.

Evidence: `experiments/ucsf-refinement-001/` includes protocol, per-seed histories/checkpoints/predictions, final comparisons, original-control comparison and verification.
