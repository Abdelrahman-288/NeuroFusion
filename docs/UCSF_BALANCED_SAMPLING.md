# UCSF balanced-sampling experiment

Completed 8 October 2026. Candidate `experiments/ucsf-balanced-train-001`; comparison `experiments/ucsf-balanced-comparison-001`.

**Decision: reject this sampling candidate and retain the engineering baseline. No application model changed.**

| Final-epoch development metric | Baseline | Balanced sampling |
|---|---:|---:|
| Mean native Dice | 0.426704 | 0.308194 |
| Mean native IoU | 0.315932 | 0.224428 |
| Mean false-positive volume, mL | 15.67175 | 3.62675 |

Three of four prespecified checks failed: mean Dice improvement, non-decreasing mean IoU, and no patient's Dice dropping by more than 0.05. The false-positive volume check passed. Patients 0038 and 0194 lost 0.21389 and 0.29996 Dice respectively; 0194 had zero overlap. Patients 0172 and 0274 improved by 0.03092 and 0.00889. Lower false-positive volume alone is insufficient when foreground agreement worsens.

The controlled change was training slice sampling: 50% probability for annotation-positive slices and 50% for empty slices, uniform within each group with replacement. Same seed 42, random initialization, 31,241-parameter model, 16/4 partition, cache, normalization, loss, Adam learning rate 0.001, five epochs and final-epoch checkpoint rule. Five checkpoints and four original-grid prediction masks are retained. Immutable baseline protocol, patient partition and cache manifest match exactly; shared model, preprocessing and metric sources also match.

Positive draws per epoch: 1,226 / 1,237 / 1,283 / 1,252 / 1,237 out of 2,480. Unique slices seen per epoch: 1,552 / 1,561 / 1,570 / 1,528 / 1,547. Replacement therefore reduced unique coverage relative to the original full shuffled epoch; the experiment tests the specified complete sampling policy, not the foreground probability in isolation. Five AMP updates were skipped automatically after overflow; 1,545 updates completed. This does not by itself prove the cause of performance instability.

Development Dice by epoch: 0.44361, 0.42710, 0.47462, 0.51960, 0.30819. Epoch four was higher, but selecting it after observing results would violate the predeclared final-epoch comparison. No retrospective checkpoint substitution is made. Training loss decreased even as final validation performance dropped.

196 tests passed. Eight viewer API tests passed after adding the comparison route. All five checkpoint hashes were checked. Reloading epoch five reproduced all four native masks and full metric dictionaries exactly. The comparison page and its three linked JSON artifacts passed HTTP checks. Restart an already-running viewer server to load the new route at `/research/ucsf/sampling/index.html`.

The next recommended stage is a predeclared training-stability experiment using the original uniform sampler and a lower learning rate, with identical partitions and final-checkpoint rules. The observed drop motivates this hypothesis but does not establish its cause. Do not expand the failed sampling candidate to confirmation seeds as if it passed. Broader acquisition, independent evaluation and expert review remain outstanding.

Overall implementation estimate stays approximately 85%; this completed experiment provides a negative result, not improved model readiness. Four repeatedly inspected development patients are not an independent test set and cannot support clinical performance claims.
