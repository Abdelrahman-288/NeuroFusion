# UCSF gradient clipping diagnostic intervention

Completed 8 October 2026. Completed run: `experiments/ucsf-gradient-clip-probe-002`. Failed original attempt retained in `experiments/ucsf-gradient-clip-probe-001`.

The initial fail-on-nonfinite protocol stopped before update 244; it has no completed checkpoint or final-volume result. A separately documented amendment restored the original AMP behavior: nonfinite gradients skip the optimizer update and reduce the scale; only finite unscaled gradients are clipped. The changed policy was saved before starting attempt 002.

Attempt 002 restored the identical epoch-four model, Adam state, scaler and RNG state. All 310 batch identities, initial probe outputs and final RNG states matched the unclipped control. Learning rate remained 0.001. Global finite gradient L2 norm was capped at 1.0 before Adam updates. 284 updates were clipped and one nonfinite update was skipped; 309 optimizer updates completed. All post-clipping finite norms were bounded.

| Group | Control Dice | Clipped Dice | Clipped mean FP mL | Empty clipped outputs |
|---|---:|---:|---:|---:|
| Four fixed training cases | 0.0000 | 0.7126 | 34.448 | 0/4 |
| Four development-validation cases | 0.0000 | 0.4996 | 34.393 | 0/4 |

Validation Dice: 0038 = 0.79286, 0172 = 0.75058, 0194 = 0.44651, 0274 = 0.00827. The final case remains a major failure: nearly matching total foreground volume conceals almost no spatial overlap (104 overlapping voxels versus 12,405 false-positive voxels). Volume agreement alone is not sufficient.

The intervention avoided the observed empty-output collapse on these eight volumes. It supports testing clipping further, but does not establish its effect from initialization or across seeds. It also does not isolate update 156 as the cause: clipping was applied throughout the epoch. The source checkpoint came from an already-inspected failure. This post hoc mechanism probe does not replace the previously failed confirmation or qualify a model for promotion.

The saved checkpoint was loaded for full native-volume evaluation. All eight saved masks were read back and reproduced their metric dictionaries. 203 regression tests passed; viewer API tests were rerun after adding the route. The report and four linked JSON artifacts passed HTTP checks. No active model or threshold changed. Restart a running viewer to load `/research/ucsf/clipping/index.html`.

Next: predeclare full-from-initialization paired-seed training with clipping and original AMP skip behavior, preserving the original data split, final-checkpoint selection and performance safeguards. Report empty-output failures explicitly alongside false positives; do not alter prior acceptance rules retroactively. Expert review, independent evaluation and broader data/model work remain pending.

Overall implementation estimate remains approximately 86%. This is useful intervention evidence, not a completed robust model or medical readiness claim.
