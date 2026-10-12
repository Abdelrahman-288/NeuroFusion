# Tumor segmentation and stroke robustness

11 October 2026. Completed the requested testing extension on the active checkpoints. Testing completion does not mean every perturbation passed or that the models are clinically robust.

All 721 tumor-positive BRISC validation images and 37 ISLES validation volumes were evaluated under six conditions each. The threshold stayed at 0.5. No training, model promotion, downloads or protected holdout use occurred.

## Tumor results

False positives and absolute size error are measured in pixels; metrics are averaged per image or volume.

| Condition | Mean Dice | Dice change | False positives | Absolute size error | New zero-overlap cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 0.6699 | +0.0000 | 1088.354 | 1326.605 | 0 |
| brightness_080 | 0.6439 | -0.0260 | 1021.105 | 1420.739 | 16 |
| brightness_120 | 0.6622 | -0.0077 | 1266.753 | 1366.527 | 7 |
| contrast_080 | 0.6648 | -0.0051 | 1134.839 | 1325.632 | 9 |
| noise_003 | 0.6409 | -0.0290 | 908.499 | 1444.756 | 26 |
| blur_100 | 0.5793 | -0.0907 | 2059.807 | 1767.505 | 31 |

Conditions flagged by the predeclared descriptive rule (mean Dice loss greater than 0.05 or any new zero-overlap case): brightness_080, brightness_120, contrast_080, noise_003, blur_100.

## Stroke results

False positives and absolute size error are measured in mL; metrics are averaged per image or volume.

| Condition | Mean Dice | Dice change | False positives | Absolute size error | New zero-overlap cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 0.3607 | +0.0000 | 8.474 | 9.553 | 0 |
| scale_080 | 0.3577 | -0.0030 | 4.208 | 7.621 | 1 |
| scale_120 | 0.3372 | -0.0235 | 13.635 | 13.847 | 0 |
| offset_020 | 0.3207 | -0.0400 | 16.861 | 16.850 | 1 |
| noise_010 | 0.3576 | -0.0031 | 9.077 | 10.017 | 0 |
| blur_100 | 0.3056 | -0.0551 | 10.236 | 10.872 | 5 |

Conditions flagged by the predeclared descriptive rule (mean Dice loss greater than 0.05 or any new zero-overlap case): scale_080, offset_020, blur_100.

## Protocol and verification

Tumor perturbations reuse the classifier suite: brightness ×0.8/1.2, contrast ×0.8 around 0.5, Gaussian noise SD0.03, and Gaussian blur sigma1 pixel, after 128×128 preprocessing. Results are scored at original image dimensions.

DWI perturbations operate after z-score normalization: scale ×0.8/1.2, offset +0.2, Gaussian noise SD0.1, and isotropic Gaussian blur sigma1 voxel. Offset and noise affect background too. No clipping or renormalization is applied. These are controlled model-input stresses, not simulations of MRI acquisition artifacts.

228 prediction archives were hash-verified and all 4548 paired case-condition metrics replayed exactly. Clean tumor and stroke predictions reproduced historical saved predictions within numerical tolerance with unchanged binary masks.

Fixed flags are descriptive, not clinically validated acceptance limits. Individual new misses remain visible even when average Dice improves. No failure is used to select a different threshold.

## Remaining limits

- Reused development partitions; tumor image groups are not verified patients.
- Positive-only tumor segmentation cannot measure no-tumor specificity.
- Synthetic post-preprocessing intensity perturbations are not scanner/site or clinical robustness.
- Active checkpoints only; improved candidates and UCSF/fusion/EEG are outside this experiment.
- No threshold tuning, downloads, holdout evaluation or promotion.

The requested robustness testing extension is implemented. Failures require separate model-quality work; independent scanner/site robustness is not established.

Evidence: `experiments/segmentation-robustness-001/` contains the frozen protocol, source hashes, coverage, per-case metrics, full predictions, summaries and verification.

Reproduce with `scripts/evaluate_segmentation_robustness.py --output <fresh-directory>`, then `scripts/verify_segmentation_robustness.py --run <directory>`.
