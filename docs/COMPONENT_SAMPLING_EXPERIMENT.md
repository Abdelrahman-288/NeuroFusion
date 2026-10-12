# Component-balanced sampling experiment

Protocol recorded before training on 2026-10-06.

Compare `dwi-component-001` against the completed `dwi-cohort-001` baseline.
The only configuration change is foreground patch-center selection: choose a
26-connected reference component uniformly, then choose a voxel uniformly inside
that component. Retain the 50% uniform spatial sampling branch. Uniform spatial
patches may contain foreground; they are not guaranteed lesion-free backgrounds.
Empty-reference studies use uniform spatial sampling only.
Balancing is within each study, not across the entire cohort. The eight-patch
budget does not guarantee selection of every component in a multi-lesion study.

Keep seed 42, the same initialization, architecture, loss, optimizer, learning
rate, study order, preprocessing, 32-voxel patch size, five epochs, eight patches
per study and frozen 174/37 development partitions. Both runs have 6,960 updates.
Component selection consumes additional random draws: this comparison uses the
same seed but does not claim identical patch locations or RNG trajectories.
No augmentation, threshold tuning, postprocessing or holdout evaluation is added.

Compare final-epoch predictions for both runs, regardless of the epoch with best
validation Dice. Report mean Dice, component recall/precision, unmatched predictions
per scan, and recall by reference size using the fixed lesion-analysis protocol.
Preserve both runs even if the new sampler performs worse. One seed and five epochs
are exploratory evidence, not a conclusive architecture or clinical result.

The previous analysis found 0/166 matched components below 0.1 mL. Sampling is a
plausible contributor, but native resolution, limited context, annotations and
model/training capacity can also matter. This experiment tests one intervention.

## Measured result

The five-epoch component-balanced run completed all 6,960 updates and passed
coverage verification. Compared with the original voxel sampler on the same 37
validation studies:

| Metric | Voxel sampler | Component sampler | Change |
|---|---:|---:|---:|
| Mean voxel Dice | 0.3157 | 0.3607 | +0.0450 |
| Mean absolute volume error | 10.50 mL | 9.55 mL | -0.94 mL |
| Lesion recall | 15.28% | 24.58% | +9.30 points |
| Lesion precision | 19.25% | 25.52% | +6.27 points |
| Lesion F1 | 0.1704 | 0.2504 | +0.0801 |
| Unmatched predicted components/scan | 5.22 | 5.84 | +0.62 |

Recall for 0.1 to below 1 mL components rose from 15.05% to 38.71%.
The below-0.1 mL group changed from 0/166 to 1/166, so the smallest-lesion
problem remains. The candidate also generated 203 zero-overlap predicted
components versus 184 for the baseline. These results support retaining the
sampler for another controlled experiment, while adding false-positive reduction
and additional seeds before treating it as a preferred model.

Full comparison: `experiments/sampling-comparison-001/index.html` and
`comparison.json`. Candidate run: `experiments/dwi-component-001/`.
