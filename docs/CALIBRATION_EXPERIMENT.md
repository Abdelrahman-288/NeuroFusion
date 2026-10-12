# Development confidence calibration

2026-10-07. Completed a temperature-scaling experiment on saved predictions from
the active baseline classifier. **Do not adopt this calibrator:** evaluation NLL
and ECE worsened on clean images and all five controlled perturbations. Predicted
classes and accuracy were unchanged. The viewer retains its existing scores.

## Protocol and provenance

The 943 BRISC validation images were split by image-similarity group using a fixed
SHA256 ordering (`calibration-v1:` prefix): 406 groups / 466 images for fitting and
407 groups / 477 images for evaluation. This keeps groups separate, not verified
patients. This validation collection was used in prior model development, so the
experiment is descriptive development evidence, not an untouched independent test.
BRISC and ISLES held-out test predictions were not loaded or generated.

One positive scalar temperature was fitted to clean fitting-subset predictions by
minimizing image-weighted negative log likelihood within [0.05,20]. Saved softmax
probabilities were converted to log probabilities with floor 1e-12, then divided
by temperature and normalized. This approximates logit scaling when probabilities
have been clipped. Identity scaling was included as a fallback. No stress-set or
evaluation labels were used in fitting. The fitted temperature was **0.845455**.

Frozen split and checkpoint hashes, row ordering, group IDs and labels were verified
against saved coverage. Inputs and source code hashes, protocol, group roles,
calibrated arrays and detailed reliability bins are saved in
`experiments/calibration-001/`. Confidence metrics are image-weighted; ECE uses ten
equal-width bins. Multiclass Brier score sums squared error across classes.

| Evaluation condition | NLL before / after | ECE before / after |
|---|---|---|
| Clean | 0.5101 / 0.5169 | 0.0273 / 0.0345 |
| Darker | 0.6253 / 0.6487 | 0.0481 / 0.0676 |
| Brighter | 0.7989 / 0.8466 | 0.1021 / 0.1148 |
| Lower contrast | 1.5788 / 1.7740 | 0.3079 / 0.3386 |
| Noise | 0.5564 / 0.5682 | 0.0197 / 0.0492 |
| Blur | 0.5104 / 0.5217 | 0.0389 / 0.0460 |

Lower is better for both metrics. This single split does not establish statistical
significance or rule out other calibration approaches. No abstention threshold or
clinical decision rule was introduced. The result does not justify confidence-based
safety claims or treating `no_tumor` as healthy.

## Reproduction

From `D:\NeuroFusion`, use a fresh output directory:

```powershell
.venv-neurofusion/Scripts/python.exe scripts/evaluate_calibration.py --output experiments/calibration-002
```

Eight new tests cover group separation/order invariance, normalization, unchanged
argmax, objective improvement on a controlled fitting case, empty reliability bins,
perfect scores and invalid inputs. All eight focused tests passed.

## Next step

Keep the calibrator out of the viewer. Prioritize actual external-image acquisition
and real alignment checks. The download endpoint returned the Aspera JavaScript
application during this stage, but file transfer was not verified and no MRI files
were acquired. Repeated tuning on this same evaluation subset would make it another
development set, not independent confirmation. Overall progress remains about 80%
while external validation and other major platform features remain incomplete.

Full regression verification: **146 tests passed** in 38.29 seconds; JUnit evidence is `experiments/calibration-001/tests.xml`.
