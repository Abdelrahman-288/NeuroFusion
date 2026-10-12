# Controlled intensity-augmentation experiment

Completed 2026-10-06. Candidate `tumor-cnn-aug-001` was trained from scratch on
3,533 BRISC training images for five epochs and 555 updates, using the same CNN,
initialization seed 42, shuffled sample order, batch size 32, Adam learning rate
0.001 and frozen partitions as `tumor-cnn-002`. Compare final epoch 5 for both.
Validation covers all 943 images. Test/quarantine images remain unused.

## Training change

An independent NumPy generator, seed 1042, applies training-only augmentation to
80% of images: contrast uniformly 0.8–1.2 around 0.5, then brightness uniformly
0.8–1.2, then independent Gaussian noise with sigma uniformly 0–0.03, clipped to
[0,1]. This is on the resized 128×128 grayscale model grid. The other 20% remain
unchanged. Augmentation randomness is separate from sample shuffling and is
saved in checkpoints. No geometric augmentation or pretrained weights are used.

## Paired results

| Condition | Baseline accuracy | Augmented accuracy | Change, percentage points |
|---|---:|---:|---:|
| Clean | 82.82% | 82.08% | −0.74 |
| Brightness ×0.8 | 77.41% | 77.62% | +0.21 |
| Brightness ×1.2 | 69.57% | 71.79% | +2.23 |
| Contrast ×0.8 | 51.11% | 82.29% | +31.18 |
| Noise sigma 0.03 | 80.06% | 81.87% | +1.80 |
| Blur sigma 1 pixel | 83.03% | 82.29% | −0.74 |

Clean macro F1 changed from 0.8228 to 0.8159. Under the contrast test, label flips
relative to each model's clean predictions decreased from 43.16% to 3.92%.
Clean meningioma recall decreased from 79.27% to 69.92%; glioma recall increased
from 62.39% to 67.89%. Aggregate robustness gains do not eliminate class tradeoffs.

The candidate substantially addresses this synthetic contrast weakness, but this
is one seed and a protocol informed by previous development results. It is not
independent external validation. Patient independence is unverified. Brightness
sensitivity remains, and segmentation/DWI robustness has not been evaluated.
The original registered viewer checkpoint remains unchanged. No automatic
promotion or inference preprocessing change was made.

## Reproduce and inspect

```powershell
Set-Location D:\NeuroFusion
.\.venv-neurofusion\Scripts\python.exe scripts/train_tumor.py --root data/raw/brisc-v6/brisc2025 --splits experiments/brisc-curated-001/splits.json --output experiments/my-augmented-run --intensity-augmentation
.\.venv-neurofusion\Scripts\python.exe scripts/evaluate_robustness.py --run experiments/my-augmented-run --output experiments/my-augmented-evaluation
```

Fresh output paths are required. Training preserves its configuration, source
copies/hashes, coverage, history, checkpoints and RNG states. Exact resumed
training of this augmented run is not yet verified. Evaluation verifies hashes,
validation coverage and reproduction of saved clean predictions before applying
the original six-condition stress protocol. Per-condition probabilities, labels,
confusion matrices, class metrics and paired flip counts are retained.

Artifacts:

- `experiments/tumor-cnn-aug-001`: trained candidate, baseline-style report and model card.
- `experiments/robustness-tumor-aug-001`: full candidate stress evaluation.
- `experiments/augmentation-comparison-001`: comparison report and metrics.
- `experiments/augmentation-comparison-verification-001`: independently recomputed
  comparison with checkpoint, protocol, label and paired coverage checks.

Candidate checkpoint SHA-256:
`a79311ac90cb6a26bd47d8c013911f2267bf31b9301399615bbefbab7a698c28`.

104 project tests pass. Augmentation tests cover repeatability, bounds, preserved
source inputs, RNG-state restoration and invalid-input rejection. Viewer routing
tests restrict comparison access to the HTML and summary JSON. The viewer links
to `/research/augmentation/index.html`.

Next: repeat the paired baseline/augmentation comparison across additional seeds,
report variability and per-class tradeoffs, and define model-promotion criteria
before changing the registered inference model. Clinical use, external evaluation,
calibration and additional specialists remain separate unfinished milestones.
