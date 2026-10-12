# Tumor model compatibility, uncertainty and qualification checks

Follow-up: [bounded classifier calibration](TUMOR_CLASSIFIER_UNCERTAINTY.md) rejected recalibration and retained the original probabilities. The unchanged scores pass limited development checks; this is not proof of improved calibration. Independent qualification remains blocked. The earlier results below are preserved.

Completed 10 October 2026 using local BRISC development data only. No downloads, protected-test inference, model replacement or expert review.

## Decision

**Checks completed; independent qualification remains blocked.** Completing an evaluation does not make a failing or unresolved requirement pass.

| Check | Result |
| --- | --- |
| application_compatibility | passed |
| segmentation_development_quality | passed |
| segmentation_development_uncertainty | passed |
| classifier_development_uncertainty | failed |
| numerical_recomputation | passed |
| patient_independent_qualification | blocked |
| segmentation_screening_specificity | not_established |

## Improved segmentation checkpoints

All three epoch-10 checkpoints were loaded through the application loader and evaluated on the same 721 positive images. Each was exercised through the actual viewer analysis path. Calibration uses 358 fit images and 363 evaluation images in disjoint image-similarity groups. These are reused development data, not independent patients.

| Seed | Compatibility | Temperature | NLL before → after | Brier before → after | Retained coverage | Dice among retained / all evaluation images |
| --- | --- | --- | --- | --- | --- | --- |
| 42 | True | 1.5 | 0.03575 → 0.02919 | 0.00729 → 0.00695 | 84.3% | 0.7906 / 0.7166 |
| 43 | True | 1.5 | 0.03407 → 0.02673 | 0.00633 → 0.00607 | 79.1% | 0.8082 / 0.7176 |
| 44 | True | 1.5 | 0.04367 → 0.03568 | 0.00861 → 0.00835 | 74.9% | 0.7992 / 0.6663 |

Binary calibration metrics use 4,096 fixed native-grid pixel samples per image, including background. Their low values must not be interpreted as lesion detection accuracy; foreground/background imbalance matters. Temperature scaling preserves the 0.5 decision boundary. Abstention is a development simulation, not enabled in the live application.

## Existing classifier

There is no newly trained improved classifier checkpoint in this experiment. The existing classifier was checked separately; segmentation calibration does not validate classification scores.

Temperature: 0.8455. Evaluation NLL: 0.5101 → 0.5169. ECE: 0.0273 → 0.0345. All uncertainty checks passed: False.

## Qualification limitations

- BRISC patient identities unavailable; image groups cannot prove patient independence
- Validation reused during model development; this is not independent qualification
- Segmentation evaluated on tumor-positive images only; screening specificity unestablished

The protected test partition was not opened to resolve these limitations. Mandatory expert review remains removed. No passing independent result or patient identity was invented. The promotion registry is unchanged.

## Evidence

- `experiments/tumor-qualification-001/protocol.json`: criteria saved before scoring.
- `summary.json` and per-seed JSON: measured results, including failed checks.
- `verification.json`: independently recomputed NLL/Brier, classifier metrics, selective risk and group separation.
- `qualification-decision.json`: explicit pass/fail/blocked disposition.
- Saved NPZ files permit numerical replay; viewer outputs demonstrate candidate integration without promotion.
