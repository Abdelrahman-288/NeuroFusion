# First BRISC classification baseline

Protocol recorded before training on 2026-10-06. Train a small 2D CNN from scratch
for five epochs with seed 42, Adam 0.001, batch size 32 and cross-entropy loss.
Use 3,533 training images and all 943 validation images from the frozen BRISC
image-group partitions. Do not load test or quarantined images. Input preprocessing
is grayscale conversion, bilinear resize to 128 x 128 and scaling to [0,1].
No augmentation, pretraining, threshold selection or class reweighting is used in
this first baseline. Every training image is visited once per epoch.

Output order: glioma, meningioma, pituitary, no_tumor. The last class must not be
interpreted as healthy or free from other brain conditions. This is a slice-level
classifier, not a 3D tumor segmentation model. The small CNN is a pipeline baseline;
EfficientNet/ConvNeXt comparisons and tumor segmentation remain future work.

Select the best checkpoint by validation macro F1, and preserve the final checkpoint
with final-epoch predictions. Report accuracy, macro F1, balanced accuracy, per-class
precision/recall and confusion matrix. Softmax outputs are uncalibrated model scores.
No claim of patient-independent or external clinical performance is supported by
these image-similarity groups. Repeated images within groups remain in the data,
so image-level scores can overweight those groups. Report that limitation explicitly.

Run command:

```powershell
Set-Location D:\NeuroFusion
& .\.venv-neurofusion\Scripts\python.exe scripts/train_tumor.py --root data/raw/brisc-v6/brisc2025 --splits experiments/brisc-curated-001/splits.json --output experiments/tumor-cnn-001
```

## Completed result

`tumor-cnn-001` failed before training because deterministic CUDA backward is
unsupported for adaptive average pooling. Fixed 4x4 average pooling gives the
same output size for our fixed input and passed the deterministic GPU test.
The corrected run is `experiments/tumor-cnn-002/`; both attempts are preserved.

The corrected 27,620-parameter CNN completed five epochs and 555 optimizer updates.
Every epoch visited all 3,533 training images. Final validation covered all 943
images, and epoch five was also best by validation macro F1.

| Measurement | Result |
|---|---:|
| Image-level accuracy | 82.82% |
| Macro F1 | 0.8228 |
| Balanced accuracy | 82.32% |
| Equal-group-weighted image accuracy | 81.94% |
| Validation similarity groups | 813 |

| Class | Validation images | Recall | F1 |
|---|---:|---:|---:|
| Glioma | 218 | 62.39% | 0.7215 |
| Meningioma | 246 | 79.27% | 0.7514 |
| Pituitary | 257 | 95.72% | 0.9077 |
| No tumor | 222 | 91.89% | 0.9107 |

The largest confusion is glioma predicted as meningioma: 69 of 218 glioma images.
This is an initial short-run research baseline, not a clinical performance claim.
All 990 test and 534 quarantined images remain unused for model training/evaluation.
The verification report checks prediction coverage, labels, group IDs, metrics,
training visits, and checkpoint/split hashes. The project suite has 51 passing tests.

Inspect `experiments/tumor-cnn-002/report/index.html` for a confusion matrix and
selected high-score errors, `MODEL_CARD.md` for limitations, and `verification.json`
for saved checks. `last.pt` and `best.pt` are retained; predictions correspond to
the final epoch. Checkpoint resume for this classifier has not yet been implemented
or verified. Further evaluation should include additional seeds and independent data.

Next platform stage: resolve BRISC mask encoding and build the 2D tumor-segmentation
pipeline, using the same image-group partitions so task copies cannot cross splits.
