# UCSF lower-learning-rate experiment

Completed 8 October 2026. Run: `experiments/ucsf-low-lr-train-001`. Comparison: `experiments/ucsf-low-lr-comparison-001`.

**Passed all four predefined development checks; candidate for paired-seed confirmation. No application model promoted.**

| Final-epoch metric | Original baseline | Lower learning rate |
|---|---:|---:|
| Mean native Dice | 0.426704 | 0.508922 |
| Mean native IoU | 0.315932 | 0.393689 |
| Mean false-positive volume, mL | 15.67175 | 13.05150 |
| Mean absolute volume error, mL | 32.24275 | 27.31225 |

Only Adam's learning rate changed: 0.001 to 0.0003. Seed 42, random initialization, architecture, loss, five epochs, batch size 8, input preparation, patient split, threshold and final-checkpoint selection remained fixed. Original uniform shuffling without replacement was restored. All 2,480 distinct training slices, including 1,015 positive and 1,465 empty slices, were used each epoch. Validation used all 620 slices from four patients. Baseline and candidate partitions, cache and shared source files matched; protocol matched after accounting for the declared learning-rate change.

Dice by patient: 0038 improved 0.73825 to 0.78380; 0172 improved 0.66861 to 0.73716; 0194 improved 0.29996 to 0.51472; 0274 remained 0.00000. The zero-overlap case remains unresolved. False-positive volume increased from 0.594 to 4.386 mL in 0194 and from 0.548 to 2.832 mL in 0274, despite an improved cohort mean. The predefined rules permit these changes; they must still be reported.

Epoch mean Dice: 0.00069, 0.42006, 0.45756, 0.42712, 0.50892. The final-minus-penultimate change was +0.08180. There was still an intermediate decrease, so this single run does not establish general training stability. Three mixed-precision updates were skipped after overflow; 1,547 updates completed. Runtime was about 72 seconds; peak PyTorch allocation 344.85 MiB, not total GPU memory.

All five checkpoints were retained and their hashes and actual optimizer learning rates verified. Reloading the final checkpoint reproduced all four masks and their metric dictionaries exactly. 196 tests passed. The viewer comparison route and three linked JSON artifacts passed HTTP checks. Restart an already-running viewer server to load `/research/ucsf/learning-rate/index.html`.

## Next stage

Confirm with paired seeds 42, 43 and 44: compare original uniform-sampling baseline at 0.001 against the same setup at 0.0003. Reuse the verified seed-42 runs and train four additional runs for seeds 43 and 44. Keep the partition, five epochs and final-checkpoint rules fixed. Require all four comparison checks to pass for each seed before accepting the change as a repeatable development improvement. A failure is reported rather than hidden by averaging. No threshold or checkpoint tuning during confirmation.

The four development patients have been repeatedly inspected. Paired seeds assess sensitivity to training randomness, not independent generalization. External cohort acquisition/assessment, expert review, broader models and datasets remain required. Candidate passing does not establish clinical readiness.

Overall rough implementation estimate: approximately 86%. This reflects a completed improvement screen and verification, not measured effort, accuracy or clinical readiness.
