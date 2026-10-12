# First DWI + ADC experiment

Protocol fixed before training on 2026-10-06.

Train `dwi-adc-001` from scratch using two input channels and compare its final
epoch against `dwi-component-001`. Both use component-balanced sampling, seed 42,
five epochs, eight patches per study, 174 training studies, 37 validation studies,
Adam 0.001, BCE plus soft Dice, native-grid preprocessing and a 0.5 threshold.
The two-channel model has 91,633 parameters versus 91,417 for DWI alone. The
first-layer shape changes initialization; this is a practical input-fusion
comparison, not a guarantee of identical weights or a conclusive causal result.

Keep all results regardless of direction. Compare final-epoch voxel Dice,
volume error, component recall/precision, unmatched predictions per scan and
size-stratified component recall under the existing fixed lesion protocol.
Do not select a better epoch for one model only. No holdout evaluation.
The 211 development pairs passed input-grid checks; selected visual checks do
not establish full anatomical registration quality. This experiment uses the
existing ISLES dataset; additional tumor and CT datasets remain separate stages.

## Completed result

The first attempt (`dwi-adc-001`) exited before a checkpoint with no diagnostic
traceback; its cause is unconfirmed and its files are preserved. The fresh run
`dwi-adc-002` completed 6,960 updates in 8.4 minutes of training/validation and
passed all study-coverage checks. All 45 project tests passed.

| Final-epoch measurement | DWI component sampler | DWI + ADC |
|---|---:|---:|
| Mean voxel Dice | 0.3607 | 0.3103 |
| Mean absolute volume error, mL | 9.55 | 7.72 |
| Matched reference components | 74/301 | 51/301 |
| Component recall | 24.58% | 16.94% |
| Component precision | 25.52% | 18.75% |
| Unmatched predictions per scan | 5.84 | 5.97 |
| Zero-overlap predicted components | 203 | 196 |
| Recall for 0.1 to below 1 mL components | 38.71% | 18.28% |

Decision: retain DWI-only as the stronger development baseline for lesion
segmentation/detection. The fusion run reduced mean absolute volume error but
regressed on Dice, component recall and precision. Both models matched only 1/166
reference components below 0.1 mL. This is one short, single-seed experiment;
it does not establish that ADC is inherently unhelpful. Future fusion experiments
should investigate normalization, training stability and multiple seeds.

Evidence:

- `experiments/fusion-comparison-001/index.html` and `comparison.json`
- `experiments/dwi-adc-002/MODEL_CARD.md`, checkpoints and prediction previews
- `experiments/lesion-analysis-fusion-001/summary.json` and `error-gallery/index.html`
- `experiments/dwi-adc-002/coverage-verification.json`

Next platform milestone: acquire and audit the next tumor dataset, establish
patient/duplicate-aware partitions, then implement the tumor specialist. This
broadens the planned multi-dataset system while preserving the current stroke
experiments. Dataset access and labels must be verified before training.
