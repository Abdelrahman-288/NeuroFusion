# First tumor-segmentation experiment

Protocol fixed before training on 2026-10-06. BRISC's audited mask histogram only
contains 0-10 and 246-255. Convert to foreground at >=128, reject intensities in
the gap, and preserve original files. This is a documented research preprocessing
choice, not a claim of expert re-annotation. Any threshold from 11 through 246
would produce the same original-resolution binary targets in this release.

Use only supplied tumor masks belonging to existing frozen classification
train/validation groups. Do not invent empty masks for no_tumor images or repartition
segmentation copies. Test and quarantined data remain unused by the model.

Train a compact 2D U-Net (channels 8/16/32), seed 42, five epochs, batch 16, Adam
0.001, BCE plus per-image soft Dice. Input: grayscale image, bilinear resize to
128x128, divide by 255. Masks: binarize at source resolution, nearest-neighbor
resize; reject masks lost by downsampling. No pretraining or augmentation.

Validation: bilinear probability restoration to original image dimensions, fixed
prediction threshold 0.5, mean per-image Dice and IoU plus per-class metrics.
Retain last and best-by-validation-Dice checkpoints; saved predictions and gallery
correspond to the final epoch. These are 2D pixel metrics, not physical tumor volume
or diagnostic accuracy. Only annotated tumor-positive images are evaluated, so
screening specificity cannot be estimated. Patient independence remains unverified.

## Completed result

Run: `experiments/tumor-seg-001/`. Five epochs and 845 optimizer updates completed
on 2,691 training pairs; every epoch evaluated all 721 validation pairs. The
31,241-parameter model reached its best validation Dice at epoch five.

| Measurement | Result |
|---|---:|
| Mean original-size Dice | 0.6699 |
| Median original-size Dice | 0.7742 |
| Mean original-size IoU | 0.5647 |
| Equal-group-weighted Dice (604 validation groups) | 0.6644 |
| Glioma mean Dice (218 images) | 0.4611 |
| Meningioma mean Dice (246 images) | 0.8140 |
| Pituitary mean Dice (257 images) | 0.7092 |

The report independently reloaded saved probabilities, restored their original
dimensions and reproduced every case metric. It verified prediction hashes,
checkpoint identity, source fingerprints, label/group mappings, epoch coverage
and partition separation. All 54 project tests pass. Test/quarantine images were
not used by the model. The source mask files remain unchanged.

Selected overlays show both partially correct regions and substantial false
positives/misses. The model is a baseline; particularly low glioma overlap and
unmeasured negative-case specificity limit its use. No physical-volume claims
are supported by these 2D JPEG images. Additional seeds, independent evaluation,
and tumor-negative segmentation evaluation remain future work.

Inspect `experiments/tumor-seg-001/report/index.html`, `MODEL_CARD.md`,
`verification.json` and `summary.json`. Probability files are float32 128x128
arrays in `predictions/*.npz`; the fixed documented resize restores them for
native-size scoring. No checkpoint-resume claim is made for this new runner.

Next platform stage: a common prediction interface and local viewer connecting
the classifier and segmenter, with explicit supported inputs and separate model
outputs. Neither output should automatically suppress or validate the other.
