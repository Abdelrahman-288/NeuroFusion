# Calibration and abstention: implemented behavior and evidence limits

11 October 2026. The inference pipeline now records an explicit uncertainty
decision, and the viewer and offline reports display it. Older results are
marked as having no recorded decision; they are not retroactively accepted.

## Current policy

Every current task abstains from a **qualified reliable conclusion** because
independent reliability has not been demonstrated. Raw model outputs remain
available and clearly labeled for research inspection. This blanket abstention
has zero qualified coverage; it is not evidence of a useful, reliable selective
predictor and does not complete scientific qualification.

The original tumor classifier additionally exposes its development screen:
uncertainty is `1 - maximum class score`, with cutoff 0.3612370491027832 fitted
on the recorded fitting groups. Higher values produce `withhold`; lower values
produce `within_development_cutoff`, never `reliable` or `healthy`. Its exact
checkpoint hash must match. A changed checkpoint makes the screen unavailable.
The rule cannot be reused for a segmenter or a different task.

## Calibration evidence

- Classifier temperature fitting previously worsened held-development NLL and
  Brier. The bounded follow-up rejected recalibration and retained original
  probabilities. The application does not relabel identity as calibration.
- At the fitting-only cutoff, the development screen retained 375/477 images
  (78.62%), with 11.2% error among retained images versus 20.13% overall. Reused
  development images do not establish new-patient risk or distribution-shift safety.
- Three improved tumor segmenters passed their development calibration checks,
  but those checkpoints are not the active segmenter and are not independently
  qualified. Their temperatures are not applied to the active checkpoint.
- Fusion calibration has failed checks; ADC-only collapsed despite apparently
  favorable calibration numbers. No fusion calibrator is deployed.
- Stroke and UCSF do not have a qualified calibration/abstention policy.

## Integration and limits

New result JSON includes policy version, decision, reason, actual classifier
binding, cutoff and whether calibration was applied. Offline reports preserve
the decision; the viewer displays it above raw scores. Predictions, masks and
model checkpoints are unchanged. Technical input checks still reject malformed
input before inference. This policy does not automatically detect wrong
modalities, out-of-distribution scans or every erroneous prediction.

The software integration is complete. **Reliable nonzero-coverage abstention and
independent calibration remain unestablished**, so the project requirement stays
partial. No independent-reliability flag is set to true. No data was downloaded
and protected evaluation data were not used.

## Verification

The focused policy, report, inference and viewer API suite passed 24 tests.
This covers cutoff boundaries, invalid scores, checkpoint changes, report
escaping, preservation in report snapshots and older results without a policy.
`experiments/uncertainty-integration-001` also passed real inference on an existing
BRISC training image and ISLES training volume. Both saved results abstain;
the tumor result includes its checkpoint-bound development screen and the stroke
result correctly marks that screen unavailable. These are operational checks,
not additional model-quality evaluation. The existing browser server was not
restarted; a running process may retain its previously imported inference code.
