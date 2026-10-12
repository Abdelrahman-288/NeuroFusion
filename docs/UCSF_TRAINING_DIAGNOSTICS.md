# UCSF training diagnostics

Completed 8 October 2026. Artifact: `experiments/ucsf-training-diagnostics-001`.

Evaluated six final checkpoints plus epochs one through four of seed 43 baseline: ten checkpoints, eight cases each, 80 case/checkpoint evaluations. The four training cases were selected by a fixed hash of patient identity before inference: 0200, 0089, 0316, 0420. All four development-validation patients were included. This is a training subset, not a whole-training-cohort estimate.

| Seed | Mode | Train-subset Dice | Validation Dice | Train FP mL | Validation FP mL |
|---|---|---:|---:|---:|---:|
| 42 | baseline | 0.4986 | 0.4267 | 10.97 | 15.67 |
| 42 | candidate | 0.7398 | 0.5089 | 13.43 | 13.05 |
| 43 | baseline | 0.0000 | 0.0000 | 0.00 | 0.00 |
| 43 | candidate | 0.6631 | 0.4391 | 51.22 | 54.00 |
| 44 | baseline | 0.0849 | 0.1241 | 1.97 | 1.38 |
| 44 | candidate | 0.5470 | 0.4864 | 94.48 | 66.56 |

Seed 43 baseline predicts empty masks on all four fixed training cases and all four validation cases at epoch five; the failure is not confined to unseen patients.

Its maximum probabilities are below 0.00015 on both groups, far below the unchanged 0.5 threshold. This is not a borderline threshold effect.

Seed 43 baseline training-subset Dice peaked at 0.6472 in epoch three, fell in epoch four, then reached zero in epoch five. Epoch-four false positives also rose sharply.

Lower-rate seed 43 and 44 runs show substantial false positives on the fixed training subset as well as validation. Their problem is not solely validation generalization.

No AMP update skips were recorded in baseline seed 43 epochs four or five; this does not exclude finite but harmful updates. Historical gradient norms were not recorded.

This supports a training failure interpretation for the seed-43 baseline on the measured subset, rather than a failure confined to generalization. It does not prove a specific cause such as learning rate, loss imbalance, precision, or a particular batch. Recorded epoch losses are averages during optimization, whereas these predictions come from end-of-epoch checkpoints; their apparent disagreement must not be treated as a metric bug without further evidence.

The probability report includes means, maxima and exact 20-bin histograms separately inside and outside supplied annotations, predicted/reference fractions, positive slices with empty outputs, and false positives on annotation-empty slices. Scores are not calibrated probabilities of disease. No threshold sweep was performed, no checkpoint replaced, and no historical experiment modified.

Source cache, reference masks and checkpoint hashes were checked. All 40 historical validation metric dictionaries matched exactly. All 200 tests passed, including threshold boundary, histogram totals, empty groups and invalid input tests. The new viewer page and four JSON links passed HTTP checks. Restart a running viewer to load `/research/ucsf/diagnostics/index.html`.

## Next stage

Replay epoch five of seed 43 baseline from its saved epoch-four checkpoint with restored optimizer, scaler and RNG states. Keep data order and all optimization settings unchanged. Record per-step batch foreground counts, unscaled gradient norms, parameter update norms, loss components and fixed-probe output summaries. Verify the final state matches the original trajectory before drawing causal conclusions. This is a diagnostic replay, not another tuned candidate. Use the trace to define a subsequent stabilization experiment; do not infer the cause from aggregate metrics alone.

Overall estimate remains approximately 86%. The failure has been narrowed and made inspectable; it has not been repaired. External evaluation, expert review and broader platform work remain outstanding.
