# Fusion underperformance: tested correction and fallback

10 October 2026. No downloads, protected-test inference or active viewer model
replacement. This is a development investigation, not a qualified fusion model.

## Weighted correction

Existing DWI, early-fusion and separate-encoder probability maps were checked
against their recorded reproduction hashes. Five weights were fixed in advance:
`(1-w)*DWI + w*(early + separate)/2`, with w = 0, 0.1, 0.25, 0.5 or 1.
Selection used only the existing 18 fitting patients. A positive weight had to
improve mean Dice, not worsen false-positive volume or absolute volume error,
and create no newly zero-Dice patient. The separate 19 development evaluation
patients were used for the selected result. Both sets were previously used in
development; this is not independent confirmation.

| Weight | Fitting Dice | Newly zero-Dice patients | Accepted |
| --- | --- | --- | --- |
| 0, DWI baseline | 0.34028 | Reference | Fallback |
| 0.10 | 0.33823 | 1 | No |
| 0.25 | 0.33347 | 1 | No |
| 0.50 | 0.33577 | 2 | No |
| 1.00 | 0.27183 | 4 | No |

All nonzero weights reduced false-positive volume but lost overlap. None passed.
The selected fallback has exactly the DWI baseline's evaluation Dice (0.38005).
This equality prevents degradation; it is not a fusion improvement or a passing
strict-improvement check.

## Application correction

`scripts/predict_advanced_fusion.py` now defaults to the DWI baseline alone.
An optionally supplied ADC must still pass alignment/input checks, but is not
used for prediction under this policy. `result.json` explicitly records
`adc_used_for_prediction: false`, the selection policy and the actual model hash.
With one member, no disagreement map is emitted. Entropy remains uncalibrated.

The original underperforming ensemble is available only through the explicit
`--experimental-ensemble` flag for reproducible research. This flag does not
bypass the DWI requirement. ADC-only remains disabled in every mode; malformed
supplied ADC remains an error rather than silently becoming a missing input.

## Verification and remaining work

The seven focused fusion/input tests passed. A real existing training volume
was run through the CLI both with and without its matched ADC. Evidence is
saved in `experiments/fusion-baseline-fallback-001` and
`experiments/fusion-baseline-fallback-dwi-001`. The weighted experiment is in
`experiments/weighted-fusion-001`.

The known default-inference regression is addressed. **The fusion-quality
requirement remains incomplete:** no tested fusion candidate improves on DWI
under the stated checks, and ADC-only has not demonstrated usable performance.
Further candidate training and qualification are still required to claim that
fusion improves accuracy. The existing single-input viewer is unchanged.
