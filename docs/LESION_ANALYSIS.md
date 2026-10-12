# Lesion-level validation analysis

Completed 2026-10-06 on the saved final-epoch predictions from `dwi-cohort-001`.
All 37 validation studies were included. No retraining or holdout inference occurred.

## Results

| Measurement | Result |
|---|---:|
| Reference components | 301 |
| Predicted components | 239 |
| One-to-one matches | 46 |
| Component recall | 15.28% |
| Component precision | 19.25% |
| Component F1 | 0.1704 |
| Unmatched reference components | 255 |
| Unmatched predicted components | 193 (5.22 per scan) |
| Predicted components with zero reference overlap | 184 |

The existing mean whole-volume Dice remains 0.3157. Component recall measures a
different property: whether individual connected regions receive a match.

| Reference volume | Count | Matched | Recall | Zero overlap |
|---|---:|---:|---:|---:|
| Below 0.1 mL | 166 | 0 | 0% | 165 |
| 0.1 to below 1 mL | 93 | 14 | 15.05% | 77 |
| 1 to below 10 mL | 34 | 24 | 70.59% | 10 |
| At least 10 mL | 8 | 8 | 100% | 0 |

The largest completely missed reference component is 2.952 mL. The largest
predicted component with no reference overlap is 39.624 mL. Small-region misses
and substantial false-positive regions both need attention. Eight matched large
components are too few to establish reliable performance on large lesions.

## Fixed protocol and interpretation

- Probability threshold 0.5, 26-connected 3D components, no size filtering.
- Maximum-cardinality one-to-one matching requires at least one overlapping voxel.
  This permissive rule can count very poor spatial agreement as detection.
- One merged prediction cannot count as multiple matched reference components.
  Unmatched predictions include split fragments, so they are not all independent
  false alarms. Zero-overlap predictions are reported separately.
- Requiring pair intersection-over-union of at least 0.10 gives 37 matches,
  recall 12.29%, precision 15.48% and F1 0.1370.
- Six-connectivity changes the reference count to 375 and gives 48 matches,
  recall 12.80%. It defines a different set of components.
- Equal-cardinality matching ties can affect which component gets a match and
  therefore size-bin allocation. Per-component matches and SciPy version are saved.
- Components approximate lesions through voxel topology. These are analyst-defined
  research metrics, not official ISLES scoring or clinically adjudicated detections.
  Screening specificity cannot be estimated from this lesion-positive validation set.

The evaluator checks dataset/split hashes, checkpoint identity, prediction geometry
and agreement with the original voxel metrics. Prediction hashes are saved per case.
Unit tests cover empty masks, misses, spurious components, merges, splits,
connectivity, overlap thresholds and invalid probabilities. All 41 project tests
passed; dependency checks also passed.

## Inspect the outputs

- `experiments/lesion-analysis-001/index.html`: all-study dashboard.
- `experiments/lesion-analysis-001/error-gallery/index.html`: six selected failures.
- `experiments/lesion-analysis-001/summary.json`: aggregate, size bins and study metrics.
- `experiments/lesion-analysis-001/cases/`: complete component-level results.
- `experiments/lesion-analysis-001/protocol.json`: fixed definitions and bindings.

Gallery examples are the three largest completely missed reference components and
three largest zero-overlap predictions. Slices maximize each selected component's
area; the gallery is deliberately selected error analysis, not representative sampling.

## Reproduce

From `D:\NeuroFusion`, using fresh output paths:

```powershell
& .\.venv-neurofusion\Scripts\python.exe scripts/evaluate_lesions.py --run experiments/dwi-cohort-001 --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache --output experiments/lesion-analysis-002
& .\.venv-neurofusion\Scripts\python.exe scripts/preview_lesion_errors.py --analysis experiments/lesion-analysis-002 --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache
```

## Next experiment

Test component-balanced lesion patch sampling against the existing voxel-based
sampling, which can favor larger components. Keep the model, seed, split, update
budget, threshold and evaluation protocol fixed for an initial controlled comparison.
Retain background patches and examine false positives alongside recall. A gain in
recall alone is insufficient. Repeat with additional seeds before drawing strong
conclusions. Do not filter tiny components to hide the current small-lesion weakness.
This experiment is proposed, not yet implemented or trained; holdout stays unused.

Implementation references: [SciPy component labeling](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.label.html)
and [maximum bipartite matching](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.maximum_bipartite_matching.html).
