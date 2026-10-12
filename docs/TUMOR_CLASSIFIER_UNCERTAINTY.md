# Classifier uncertainty follow-up — 10 October 2026

The previous temperature fit worsened NLL and Brier on the separate development
evaluation groups. This follow-up tested a fixed grid of 25 temperature/uniform
mixing combinations. A candidate had to avoid worsening either score in each
of five image-group folds drawn only from the fitting subset. The selection was
saved before evaluating the outer subset. Those outer groups have previously
been examined; this remains exploratory development work, not independent
confirmation.

## Result

The selector retained **identity: original probabilities, no recalibration**.
No nonidentity option satisfied all fitting-fold checks. Retaining the baseline
prevents the previous calibration regression; it does not demonstrate a new,
better calibrated classifier. The previous failed experiment remains preserved.

On the 477 outer development images:

| Metric | Result |
| --- | --- |
| Accuracy across all cases | 79.87% |
| NLL | 0.51013, unchanged |
| Brier score | 0.27730, unchanged |
| 10-bin ECE | 0.02726, unchanged |
| Retained images at fitting-only confidence threshold | 375/477 (78.62%) |
| Error among retained images | 11.20% |
| Error across all images | 20.13% |

The abstention simulation meets its limited development criteria. Rejected
cases still require another handling path; they are not counted as correct.
These values do not establish reliable confidence under distribution shift or
patient-independent performance. No model weights, live probability outputs or
live abstention behavior were changed.

## Qualification disposition

- All three improved segmenters previously passed compatibility and development
  uncertainty checks.
- Classifier recalibration was rejected; the original scores were retained.
- The retained classifier passed the stated development non-regression, ECE and
  selective-risk checks. Non-regression is automatic for an identity mapping,
  so this must not be described as evidence of calibration improvement.
- Patient-independent qualification remains unresolved because BRISC patient
  identities are unavailable and validation data have been reused.
- Segmentation screening specificity remains unestablished: masks were evaluated
  on tumor-positive images only.

No promotion or full tumor qualification is claimed. No downloads or protected
test-image inference were performed.

Evidence: `experiments/tumor-classifier-uncertainty-003/` contains the protocol,
selection, summary, saved evaluation and replay verification. Run `002` stopped
before selection or outer evaluation because the nominal identity operation
renormalized float32 probabilities. The corrected identity copies the original
probabilities exactly; its regression test now passes. The failed run is retained.
