# Three-seed baseline and augmentation evaluation

Protocol recorded 2026-10-06 in `configs/multiseed_protocol.json` and copied to
`experiments/multiseed-001/protocol.json` before starting seeds 43 and 44.
Seed 42 was already observed; this is not a wholly prospective experiment.

The six runs pair baseline and intensity-augmented training at seeds 42, 43 and
44. Each uses 3,533 training images, five epochs, 555 updates, final checkpoint,
the same architecture and optimizer, and matching sample shuffling within each
pair. Augmentation uses its own generator with seed = training seed + 1000.
All six fixed stress conditions use the same 943 validation images, sorted order
and perturbation seed. Held-out test and quarantine images remain unused.

## Interpretation

The summary reports mean, sample standard deviation, minimum and maximum across
three training seeds, plus paired differences. Standard deviations are not
confidence intervals. Reusing the same validation images across seeds does not
create three independent patient cohorts. Only the tumor classifier is covered.

The engineering screening criteria require mean clean accuracy loss no worse than
1 percentage point, mean clean macro-F1 loss no worse than 0.01, no class's mean
clean recall loss worse than 5 percentage points, mean accuracy gain across the
five perturbed conditions at least 2 percentage points, and no individual seed's
clean accuracy loss worse than 3 percentage points. These are development choices,
not clinical acceptance standards. Passing only supports further independent
evaluation; it cannot automatically replace the viewer checkpoint.

## Reproduction and evidence

Use `scripts/train_tumor.py --seed 43` or `--seed 44`, adding
`--intensity-augmentation` for each paired candidate and fresh output paths.
Then run `scripts/evaluate_robustness.py --run <run> --output <fresh-output>`.
`scripts/summarize_multiseed.py` validates the six artifacts and builds the report
using the recorded paths. It refuses to overwrite an existing summary.

Seed-42 artifacts are reused from the prior experiments. New training and
evaluation logs, the fixed protocol and the aggregated report are stored under
`experiments/multiseed-001`. Every training run preserves configuration, source
snapshots, coverage, RNG state, history and checkpoints. The aggregation verifies
checkpoint/split hashes, paired controls, all validation labels and coverage,
and recomputes all metrics from saved probabilities.

The first seed-43 baseline evaluation stopped because its clean scores differed
from saved training-validation scores by 2.92e-5. That partial output is preserved
in `robustness-baseline-seed43-001`; the successful rerun uses suffix `002`.
The harness normalizes on CPU and training validation normalizes on GPU. The
reproduction check now requires both max score difference ≤1e-4 and identical
predicted classes. Earlier seed-42 outputs also pass this combined criterion.
This tolerance adjustment affects numerical verification only, not images,
checkpoints, evaluation conditions or labels. It is disclosed rather than hidden.

Results and screening decisions are in the linked HTML/JSON report at
`/research/multiseed/index.html`. The viewer model is not changed by this stage.
External validation, calibration, segmentation/DWI robustness and broader
specialists remain unfinished.

## Completed results (2026-10-07)

| Condition | Baseline mean accuracy | Augmented mean accuracy | Paired change (pp) |
|---|---:|---:|---:|
| Clean | 83.28% | 81.44% | -1.84 |
| Brightness x0.8 | 70.48% | 77.87% | +7.39 |
| Brightness x1.2 | 72.15% | 73.56% | +1.41 |
| Contrast x0.8 | 54.01% | 81.37% | +27.36 |
| Noise sigma 0.03 | 82.18% | 81.34% | -0.85 |
| Blur sigma 1 | 83.00% | 81.48% | -1.52 |

Clean mean accuracy across seeds is 83.28% ± 0.89 percentage points for the
baseline and 81.44% ± 0.56 for augmentation (sample standard deviations).
The augmentation policy fails four of five development gates: mean clean
accuracy, mean clean macro F1, per-class mean clean recall and worst-seed clean
accuracy loss. It passes the mean perturbed-accuracy improvement gate. Mean
clean recall falls 5.50 points for glioma and 5.42 points for meningioma.

Decision: retain the existing viewer model. Do not select a different seed's
checkpoint merely because its validation accuracy is higher. All six-condition
metrics were recomputed and all paired protocol, checkpoint, coverage and label
checks passed. 107 automated tests pass, with focused route/screening tests also
rerun after their final changes.

Next: a narrower training-policy experiment addressing the clean/per-class
regressions, with a fixed protocol and the same seed pairs. Further tuning reuses
development data and therefore still requires independent external validation.
