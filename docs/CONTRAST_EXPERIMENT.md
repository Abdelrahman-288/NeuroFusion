# Narrower contrast-only training experiment

Protocol fixed before these runs on 2026-10-07. Following the combined intensity
policy's clean/per-class regressions, this experiment applies contrast augmentation
alone with probability 0.3 per training image. Contrast factors are uniformly
sampled from 0.8–1.0 around intensity 0.5 on the normalized 128×128 grayscale grid.
The remaining 70% are unchanged. No brightness, noise or geometric augmentation.

Three new candidate runs use seeds 42, 43 and 44, each with independent augmentation
RNG seed = training seed + 1000. The original matching baseline runs are reused.
Architecture, optimizer, learning rate, sample shuffling, five-epoch duration,
555 updates, final-epoch comparison and frozen partitions remain fixed. Each
candidate is evaluated on the same six conditions and 943 validation images.
Test and quarantine images are not loaded.

The screening criteria from the prior three-seed experiment are unchanged. The
saved protocol is `experiments/contrast-multiseed-001/protocol.json`. This policy
was informed by previous development results; it is not independent validation.
Repeated tuning increases the need for an external evaluation. Passing the
engineering screen would not automatically change the viewer or establish
clinical readiness.

## Reproduce

```powershell
Set-Location D:\NeuroFusion
.\.venv-neurofusion\Scripts\python.exe scripts/train_tumor.py --root data/raw/brisc-v6/brisc2025 --splits experiments/brisc-curated-001/splits.json --output experiments/my-contrast-run --seed 42 --contrast-augmentation
.\.venv-neurofusion\Scripts\python.exe scripts/evaluate_robustness.py --run experiments/my-contrast-run --output experiments/my-contrast-eval
```

Use fresh output paths and repeat with seeds 43 and 44. The contrast flag and
combined-intensity flag are mutually exclusive. Existing baseline and combined
augmentation behavior remains available. Augmentation state is checkpointed.

`scripts/summarize_multiseed.py --contrast-only` verifies this study's canonical
run paths and writes a fresh aggregate summary. It checks the exact contrast
policy, frozen split/checkpoint hashes, paired controls, training/validation
coverage, reference labels, clean reproduction and saved stress metrics.

Run folders are `tumor-contrast-seed<seed>-001` and
`robustness-contrast-seed<seed>-001` under experiments. Logs, protocol, summary and
HTML report are under `experiments/contrast-multiseed-001`. The local viewer links
to `/research/contrast/index.html`. Reports display seed mean and sample standard
deviation, not confidence intervals or patient-level uncertainty.

## Completed results

| Condition | Baseline mean accuracy | Contrast-only mean accuracy | Change (pp) |
|---|---:|---:|---:|
| Clean | 83.28% | 82.96% | -0.32 |
| Brightness x0.8 | 70.48% | 67.62% | -2.86 |
| Brightness x1.2 | 72.15% | 72.78% | +0.64 |
| Contrast x0.8 | 54.01% | 80.03% | +26.02 |
| Noise sigma 0.03 | 82.18% | 82.61% | +0.42 |
| Blur sigma 1 | 83.00% | 81.72% | -1.27 |

All five previously fixed development gates pass. Clean mean loss is 0.32 points,
compared with 1.84 points for the combined-intensity policy. This does not make
it uniformly superior: darker-image performance falls 2.86 points on average;
meningioma mean clean recall falls 4.07 points (worst seed: 7.72 points). The
screen constrains mean per-class recall, not every class at every seed. Mean
glioma recall improves 3.36 points. Passing thresholds does not erase regressions.

Decision: retain the existing viewer model, preserve this candidate for independent
evaluation, and avoid selecting the highest-scoring validation seed as a shortcut.
No checkpoint registration or inference preprocessing was changed. Further tuning
on this validation set should not be mistaken for fresh evidence.

108 automated tests passed. Focused API/augmentation tests passed after the final
route changes. All six models' saved metrics were independently recomputed;
paired controls, exact policy, hashes, labels and coverage checks passed. Three
new candidate models were trained for five epochs each. Baselines were reused.
The 990-image BRISC test partition remains untouched. These results do not assess
segmentation, DWI robustness or medical deployment readiness.

Next: independent-evaluation dataset readiness and overlap auditing, before any
external generalization claim or change to the viewer's registered model.
