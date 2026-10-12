# UCSF exact epoch-five replay

Completed 8 October 2026. Artifact: `experiments/ucsf-epoch-replay-001`.

Replayed seed 43 baseline epoch five from its epoch-four checkpoint. The final model tensors, optimizer state, AMP scaler state, CPU/CUDA RNG states, loader RNG state, epoch loss and skipped-update count matched the original exactly. Eight checks passed. The 310-update trace therefore describes a reproduction of the original failure, rather than a separately trained approximation.

## Findings

Eight fixed training probes were used: median positive and median empty axial slice from each of the four previously hash-selected training patients. Probe predictions became persistently empty at threshold 0.5 after update 157 and remained empty for all 154 remaining updates. The precise transition is established for the probes, not every original volume at that moment. The final whole-volume failure was established in the prior diagnostic stage.

Update 156 had the largest unscaled gradient L2 norm (24.9232), about 27.5 times the epoch median (0.90624), and the largest parameter update L2 norm (0.133119). It contained one positive slice among eight and 938 foreground pixels. After that update, the probes still had 559 predicted pixels and maximum score 0.98583. Update 157 contained two positive slices and 5,588 foreground pixels; afterward the probes had zero predicted pixels and maximum score 0.008779. Its gradient norm was 0.92432 and update norm 0.120124. Updates 152 and 135 also had large finite gradients earlier in the epoch.

All gradients were finite, and no AMP steps were skipped in this replay. This excludes an AMP-skipped-update explanation for this epoch, but does not prove a precision-independent cause. Finite updates and Adam momentum can still have large effects; the trace alone does not establish which mechanism caused the collapse. An all-empty batch did not directly trigger either of the two identified updates.

Loss components, batch patient/slice identities, foreground counts, gradient norms, parameter update norms, scaler values and probe statistics are retained in trace.jsonl. The viewer report plots exact probe traces and shows the transition window. Historical experiments were not changed and no model was promoted.

201 regression tests passed, including exact nested checkpoint comparisons. The new viewer report and four JSON links passed HTTP checks. Restart a running viewer server to load `/research/ucsf/replay/index.html`.

## Next stage

Run a predeclared diagnostic intervention from the same epoch-four state, changing only unscaled gradient clipping to maximum L2 norm 1.0 before Adam updates. Keep the same batches, learning rate, loss, precision and threshold. Log identical traces and evaluate all four fixed training volumes and all four development-validation volumes. This is a post hoc mechanism probe, not a new deployable model. If it avoids empty outputs, that supports further investigation but does not prove general effectiveness; then require full-from-initialization paired-seed experiments and unchanged performance safeguards. Do not replace the failed confirmation retroactively.

Overall implementation estimate remains approximately 86%. The failure has been reproduced and localized, but no fix has yet been demonstrated. Clinical readiness and independent generalization are not established.
