# First development robustness evaluation

Completed 2026-10-06. This evaluation covers only the pinned four-class tumor
classifier on the full frozen BRISC validation partition: 943 images, 813 image
similarity groups, six conditions and 5,658 predictions. No test or quarantine
images were loaded. This is a development stress test, not external validation.

## Measured results

| Condition | Accuracy | Macro F1 | Label flips vs clean |
|---|---:|---:|---:|
| Clean | 82.82% | 0.8228 | 0.00% |
| Brightness ×0.8 | 77.41% | 0.7654 | 25.13% |
| Brightness ×1.2 | 69.57% | 0.6680 | 21.21% |
| Contrast ×0.8 around 0.5 | 51.11% | 0.3782 | 43.16% |
| Gaussian noise, sigma 0.03 | 80.06% | 0.7891 | 5.62% |
| Gaussian blur, sigma 1 pixel | 83.03% | 0.8255 | 3.29% |

The tested contrast perturbation reduced accuracy by 31.71 percentage points:
314 clean-correct predictions became wrong, while 15 clean-wrong predictions
became correct. This suggests sensitivity to the intensity representation under
this protocol. It does not establish how the model behaves on a different scanner
or hospital. Slight improvement under blur is not evidence for deploying blur as
a fix. No checkpoint or inference preprocessing was changed by this experiment.

## Reproduction

```powershell
Set-Location D:\NeuroFusion
.\.venv-neurofusion\Scripts\python.exe scripts/evaluate_robustness.py --output experiments\robustness-tumor-repeat
```

Choose a fresh output path. The script checks the frozen split hash and each input
file hash using the development-only loader, loads the registered checkpoint by
hash, and reproduces the clean baseline before testing perturbations. The maximum
clean probability difference from the earlier saved baseline was 6.02e-6, below
the predefined 1e-5 tolerance; clean accuracy and macro F1 matched.

Perturbations operate after grayscale conversion and bilinear resizing to the
128×128 model grid, on [0,1] floats. Brightness multiplies intensities; contrast
uses `(x-0.5)*0.8+0.5`. Noise uses NumPy's seeded generator (20261006), standard
deviation 0.03, in the stable sorted image order. Blur uses sigma 1 pixel on the
spatial dimensions only and reflected boundaries. All outputs are clipped to
[0,1]. References remain unchanged; there are no geometric transformations.

## Evidence and access

`experiments/robustness-tumor-001` contains configuration, exact validation coverage,
input/checkpoint/split hashes, source copies and hashes, per-condition probability
arrays, labels, metrics, verification and an HTML summary. Metrics include per-class
precision/recall/F1, confusion matrices, label flips, correct-to-wrong and
wrong-to-correct counts, score shifts and equal-similarity-group-weighted accuracy.
The latter is not patient-level accuracy. Saved metrics were independently
recomputed from exported arrays for all six conditions.

The viewer links to `/research/robustness/index.html`. Its research route exposes
only this report and three supporting JSON files, not arbitrary experiment files.
101 tests pass across the project, including deterministic perturbations, bounded
outputs, no cross-image blur, paired errors, group weighting and route restrictions.

## Remaining work

No segmentation or DWI robustness experiment, clinical validation, confidence
intervals, calibrated uncertainty or learned out-of-distribution detector is
included. Image similarity groups do not prove patient independence. The quality
checks from the previous stage do not guarantee robustness to these perturbations.

Next: a controlled classifier training experiment using intensity augmentation,
compared against this exact clean/stress protocol. Keep the original checkpoint,
run configuration and test holdout intact; report clean-performance tradeoffs and
avoid selecting a fix solely from the single largest observed weakness.
