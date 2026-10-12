# UCSF clipping from initialization: three-seed confirmation

Current follow-up: [three-seed refinement](UCSF_REFINEMENT.md) uses only existing data. Missing-dataset branches and mandatory expert review are no longer required; the historical scope statements below are superseded by `CURRENT_PLAN.md`. Earlier failed comparisons remain failed.

Completed 8 October 2026. Artifact: `experiments/ucsf-clipping-confirmation-001`.

**Decision: confirmation failed; retain baseline. No active model was changed.**

| Seed | Baseline Dice | Clipped Dice | Baseline FP mL | Clipped FP mL | Checks passed |
|---|---:|---:|---:|---:|---:|
| 42 | 0.426704 | 0.461694 | 15.672 | 5.793 | 4/4 |
| 43 | 0.000000 | 0.493095 | 0.000 | 26.018 | 3/4 |
| 44 | 0.124062 | 0.439852 | 1.379 | 25.412 | 3/4 |

Seed 44 attempt 001 exited with Windows code 3221226505 before any epoch checkpoint, without a Python traceback. Cause is unknown. It is retained with failure.json; attempt 002 restarted with identical settings.

Three five-epoch models were trained from random initialization with seeds 42, 43 and 44. Each is paired with its existing unclipped run. Only finite unscaled gradient clipping (global L2 maximum 1.0) was added. Adam learning rate 0.001, original uniform sampling, batch size, architecture, AMP skipped-update behavior, loss, data split, threshold 0.5 and final-checkpoint selection were preserved. No warm start from the successful diagnostic probe was used.

Acceptance required all four previously defined checks separately in every seed. Avoiding empty predictions is a separate diagnostic observation, not a substitute for overlap and false-positive checks. An empty-output baseline's zero false positives does not make it useful; all failures and the original rules are retained. These repeatedly reviewed four validation patients remain development data.

All 15 new checkpoint hashes and actual optimizer learning rates were verified. All 12 saved final native predictions and metric dictionaries were reproduced by reloading checkpoints. Shared source, partitions, cache and complete per-epoch training coverage matched the controls; clipping norms stayed within the specified bound. The regression suite passed 203 tests, and the report plus three linked JSON artifacts passed HTTP checks. Restart a running viewer to load `/research/ucsf/clipping-confirmation/index.html`.

## Progress reporting correction

This stage is 4/4 complete: train three seeds; verify saved predictions; apply prespecified comparisons; publish the report and viewer link. These deliverables are equally counted for task completion only, not time or model quality. The historical overall 86% was an informal estimate without a weighted full roadmap. It should not be repeated as a measured completion percentage. `docs/progress_tracker.json` now separates completed work from readiness.

Infrastructure, data intake and research diagnostics have progressed even when experiments fail. The full project still requires robust model qualification, additional planned disease/data/model branches, independent evaluation, expert review, and deployment readiness. Stage completion must not imply those are finished.

## Next work

Use the completed stabilization evidence to set a bounded model-qualification plan, rather than repeatedly extending experiments on the same four patients. Record explicit acceptance criteria and outstanding failures, then prioritize the independent cohort/data requirements and the missing product/model milestones. Any revised criteria constitute a new prospective protocol; previous failed comparisons remain failed. No clinical performance claim or automatic promotion follows from this stage.
