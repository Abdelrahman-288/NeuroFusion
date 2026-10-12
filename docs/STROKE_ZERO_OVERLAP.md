# Stroke threshold confirmation and zero-overlap investigation

Completed development audit on 10 October 2026 using all 37 existing validation
patients. No downloads, protected test-set evaluation or model promotion.

## Decision

**Reject threshold 0.65 for promotion. Keep the original active model.** Its
aggregate improvement hides newly missed patients. The original six acceptance
checks are now supplemented in this audit by (1) no increase in zero-Dice cases
and (2) no newly zero-Dice patient relative to the baseline. These additional
checks address the regression; they do not erase the original reported results.

| Metric | Active baseline: epoch 5, 0.50 | Epoch 10, 0.65 | Fixed correction: epoch 10, 0.55 plus filter |
| --- | --- | --- | --- |
| Mean Dice | 0.36070 | 0.38325 | 0.38130 |
| Mean absolute volume error, mL | 9.5529 | 7.8996 | 8.9493 |
| Mean false-positive volume, mL | 8.4738 | 6.2609 | 7.9023 |
| Lesion recall | 0.24585 | 0.25249 | 0.26246 |
| Lesion precision | 0.25517 | 0.26761 | 0.27915 |
| Non-overlapping predicted components/scan | 5.48649 | 5.08108 | 5.16216 |
| Zero-Dice patients | 4 | 6 | 4 |
| Newly zero-Dice patients vs baseline | — | 3 | 1 |
| Expanded acceptance checks | Reference | 6/8 | 7/8 |

“Zero-Dice patients” means no predicted voxel overlaps any reference lesion in
that patient's scan. “Non-overlapping components” counts individual predicted
regions without reference overlap; these are different failure measures.

## Cause and correction tested

At 0.65, patients 0002, 0098 and 0234 lose all overlap. Their highest candidate
probabilities inside reference lesions are respectively 0.5454, 0.6250 and
0.6164. Raising the threshold removes their weak predictions. Patient 0068
improves from zero overlap, partly concealing these regressions in totals.

One correction was fixed before evaluation: lower the threshold to 0.55 and
remove 26-connected components smaller than 0.01 mL. It restores overlap for
0098 and 0234 and reduces excess small false-positive components. It still
misses 0002, whose maximum probability is below 0.55. It also removes a tiny
overlap in already-baseline-missed case 0093, illustrating the small-lesion cost
of component filtering. It is rejected rather than selected because its total
zero-Dice count happens to match the baseline.

This filter never reads reference labels during prediction. Reference masks are
used only for evaluation and this retrospective explanation. No patient-specific
threshold or label-informed rescue rule is deployed.

## What is complete and what remains

- Numerical recheck of the selected threshold, patient-level regression audit,
  one fixed correction and an explicit reject/retain decision are complete.
- The selected 0.65 threshold is **not confirmed as acceptable**.
- The correction addresses two of three new misses but does not solve the final
  patient-level regression. The active baseline itself still misses four cases.
- Cross-seed confirmation and independent evaluation have not been performed.
  They should follow a candidate that passes the strengthened development checks.
- Further model work must use a new recorded protocol and matched controls;
  repeatedly lowering a threshold to fit these known cases is not confirmation.

Evidence: `experiments/stroke-zero-overlap-001/` contains `protocol.json`, all
per-patient cases, source hashes, zero-overlap diagnostics, results and replay
verification. The .65 metrics reproduce the original threshold study. No
checkpoint or inference threshold in the application was changed.
