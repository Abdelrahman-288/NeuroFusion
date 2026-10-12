# Advanced fusion development experiment

Current policy: [weighted-fusion follow-up and fallback](FUSION_NONREGRESSION.md). The CLI now defaults to the DWI baseline because all tested fusion candidates failed improvement checks. The original ensemble described below requires `--experimental-ensemble`. ADC-only remains disabled. Historical results are preserved.

Separate-encoder fusion, equal-weight ensembles, simulated missing-input inference, and patient-partitioned calibration/abstention evaluation are implemented. Independent reliability and deployment qualification remain unestablished.

| Mode | Dice | Volume error mL | Uncertainty checks |
|---|---:|---:|---:|
| both | 0.3237 | 7.337 | 3/5 |
| missing_adc | 0.3324 | 8.939 | 4/5 |
| missing_dwi | 0.0000 | 11.872 | 5/5 |

## Scope
Five epochs, seed 42, 174 training patients, 37 validation patients. Separate encoder has 105,105 parameters versus 91,417 DWI-only and 91,633 early-fusion parameters; this is not a capacity-matched causal ablation. Final epoch selected before training. Calibration temperatures and abstention cutoff fitted on 18 validation patients, assessed on 19 different validation patients. These are reused development data, not independent evaluation. Each availability pattern has its own fitted temperature and cutoff.

Unavailable encoders are gated; modality absence is explicit. DWI-only uses DWI baseline plus separate encoder; ADC-only uses the separate encoder alone and does not emit ensemble variance. Both missing rejects. Malformed or misaligned supplied inputs must be rejected, never silently treated as missing. Missing-DWI evaluation uses the paired DWI reference grid and support, which limits its applicability to standalone ADC inputs.

All three complete-input checkpoints are replayed on every validation patient. Native-grid probabilities, entropy and multi-member variance are saved under experiments/advanced-fusion-001/evaluation. Entropy is not calibrated error probability. Do not use a low uncertainty value as proof of health.

## Evidence
- experiments/advanced-fusion-001/protocol.json
- experiments/advanced-fusion-001/summary.json
- experiments/advanced-fusion-001/checkpoint-reproduction.json
- experiments/separate-encoder-001/coverage-verification.json

No model promotion or independent test inference occurred. Original baselines remain active.

## Acceptance decision
Not qualified. ADC-only produced zero Dice on all 37 cases despite passing the aggregate uncertainty checks. This demonstrates that those checks cannot establish usable segmentation or clinical reliability. Both-input and DWI-only ensembles underperform the DWI baseline on mean Dice. Both-input calibration fails Brier/ECE; DWI-only calibration fails ECE. All results are preserved. No model/calibrator/abstention rule is promoted.

## Experimental local inference
Run `.venv-neurofusion/Scripts/python.exe scripts/predict_advanced_fusion.py --dwi PATH --adc PATH --output FRESH_DIRECTORY`. ADC is optional; DWI is required because ADC-only failed evaluation and is disabled. Malformed data, conflicting orientation forms or mismatched physical grids reject. This CLI writes raw probability, entropy and multi-member variance maps; it does not apply calibration or make abstention/clinical decisions. Keep provisional independent-evaluation cases out of this command.

Verification: 253 tests passed in the full suite; 17 focused tests passed after the ADC-only rejection policy. All 111 member/case predictions replayed, all 111 mode/case outputs and their calibration samples verified, and paired CLI inference matched the saved evaluation output. No viewer restart was attempted; the saved HTML report is directly available, and the new route requires loading the updated server.
