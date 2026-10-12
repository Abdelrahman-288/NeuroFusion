# UCSF paired-seed confirmation

Completed 8 October 2026. Artifact: `experiments/ucsf-lr-confirmation-001`.

**Decision: confirmation failed; retain baseline. No model promoted.**

| Seed | Baseline Dice | Lower-LR Dice | Baseline FP mL | Lower-LR FP mL | Checks passed |
|---|---:|---:|---:|---:|---:|
| 42 | 0.426704 | 0.508922 | 15.672 | 13.052 | 4/4 |
| 43 | 0.000000 | 0.439077 | 0.000 | 53.999 | 3/4 |
| 44 | 0.124062 | 0.486357 | 1.379 | 66.558 | 3/4 |

The predeclared rule required all four checks to pass separately for seeds 42, 43 and 44. Failed seeds cannot be hidden by averaging. Seed 42 was reused from the candidate-selection experiment; four additional five-epoch runs were trained for seeds 43 and 44. Each pair compares Adam 0.001 versus 0.0003, using identical initialization seed, original uniform sampling, all 2,480 training slices each epoch, the same 16/4 patient partition, and final-epoch selection. No checkpoint, threshold or seed was selected after seeing outcomes.

The seed-43 baseline predicted empty masks for all four patients. Its zero false-positive volume is therefore not evidence of a useful model. Lower LR improves overlap for that seed but increases mean false-positive volume to 53.999 mL, failing the predefined volume guardrail. Preserve both facts; do not reinterpret the protocol after the result. Inspect all patient-level metrics in summary.json.

Checks verified patient partitions, cache hashes, intended seed and learning rate, shared architecture/preprocessing source, all checkpoint hashes, and full training-slice coverage. Each new final checkpoint was reloaded and reproduced all four saved native masks and metric dictionaries exactly. Twenty new checkpoints and sixteen final prediction masks are retained. All 198 regression tests passed; confirmation aggregation tests were rerun after clarifying per-seed decision wording. The report and three JSON links passed HTTP verification. Restart an already-running local viewer to load `/research/ucsf/confirmation/index.html`.

Three seeds reuse the same four development patients, not twelve independent patients. Repeated inspection and candidate selection on this cohort prevent an independent generalization claim. These are numeric annotation-union comparisons, not diagnostic accuracy.

## Next stage

Investigate the empty-output training failure before further tuning: evaluate original-grid foreground coverage on a fixed training subset and all development patients, inspect probability distributions and gradients/checkpoint histories, and distinguish training failure from generalization failure. Keep the failed comparisons intact. Any revised acceptance rule or training schedule must be declared as a new experiment; it cannot retroactively make this confirmation pass. Broader data acquisition, independent cohort evaluation and expert review remain required.

Overall implementation estimate stays approximately 86%. Confirmation is complete, but the candidate has not earned promotion. This estimate is not a measure of clinical readiness.
