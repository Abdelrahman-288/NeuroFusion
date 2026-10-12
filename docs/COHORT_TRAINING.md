# Full-cohort DWI training

Updated 2026-10-06. This runner uses every frozen training study and every validation
study. It explicitly blocks holdout access. Results are development metrics, not
clinical validation. Read the final `summary.json` for measured outcomes.

The first run completed successfully: mean validation Dice 0.3157, median 0.2783,
mean absolute volume error 10.50 mL after five epochs. Mean Dice increased from
0.1647 in epoch 1 on the same 37 validation studies. Training plus validation took
8.0 minutes after 1.4 minutes of preprocessing; peak process working set was
1.09 GiB. The lowest-Dice example missed its reference lesion; case performance
is uneven. These results require substantial improvement.

33 automated tests pass, the full-run coverage check passes, and exact resume
matches the synthetic uninterrupted control. The complete measured model card is
`experiments/dwi-cohort-001/MODEL_CARD.md`.

## Run design

- 174 training studies, 37 validation studies; 37 holdout subjects remain unused.
- Five epochs, eight patch updates per study per epoch: 6,960 optimizer steps.
- Each epoch visits all training studies exactly once in a seeded shuffled order.
- The same 91,417-parameter DWI U-Net used in the verified debugging pipeline.
- 32-cubed patches, BCE plus soft Dice, Adam 0.001, mixed precision, seed 42.
- Training sampling is 50% lesion-centered when a lesion exists; other patches
  are uniformly spatial. No augmentation in this initial full-cohort baseline.
- Native spacing and nonzero per-image normalization. FLAIR remains excluded.
- Every epoch evaluates all validation volumes with overlapping windows at a
  fixed probability threshold of 0.5; no validation-label-based patch selection.
- Mean/median Dice, voxel metrics, per-case and mean absolute volume error are
  recorded. Connected-component/lesion-level metrics remain future work.

## Memory and integrity

`StudyStore` preprocesses one study at a time, writes NumPy arrays to disk, and
returns read-only memory maps for the current study. It never caches the entire
cohort's voxels in RAM. Training patches and sliding-window inference use one
GPU patch at a time. Windows process peak working set and PyTorch peak allocated
GPU bytes are recorded in the completed run summary; these measure different
things and GPU allocated bytes are not the entire driver's reservation.

The cache is namespaced by preprocessing version and manifest hash. Raw DWI/mask
hashes are checked against the manifest, and stored cache checksums are checked
on first access in each process. Checks do not replace a read-only dataset policy:
do not modify source or cached data during a run. Interrupted cache construction
fails explicitly; use a new cache directory if an incomplete entry needs rebuilding.
The development loader accepts only training and validation partitions.

## Commands

```powershell
cd D:\NeuroFusion
$python = '.\.venv-neurofusion\Scripts\python.exe'
& $python scripts/train_cohort.py --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache --output experiments/my-cohort-001 --epochs 5 --patches-per-study 8
```

To continue from the last completed epoch, use a new output directory and a larger
total epoch target. Model, optimizer, scaler, RNG state and histories are restored:

```powershell
& $python scripts/train_cohort.py --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache --output experiments/my-cohort-002 --epochs 6 --patches-per-study 8 --resume experiments/my-cohort-001/last.pt
```

Checkpointing occurs at completed epoch boundaries. An interruption partway through
an epoch requires repeating that epoch. An interruption in the first epoch has
no training checkpoint yet. Keep the same configuration and data for resumption.
The exact resume implementation was tested against an uninterrupted two-epoch
synthetic control: `experiments/cohort-resume-verification-001.json`.

## Local artifacts

Current run: `experiments/dwi-cohort-001/`.

- `progress.html`: refreshable loss and validation view.
- `config.json`, `run-request.json`: data bindings and planned run settings.
- `history.json`: individual patch losses and sampled patient identities.
- `validation.json`: all epochs and all per-case results.
- `last.pt`: final completed epoch; `best.pt`: highest mean validation Dice.
- `predictions/`: final-epoch validation probabilities in original scan geometry.
- `summary.json`: completed results and measured resource use.
- `source/`, `source-hashes.json`, `environment.txt`: reproducibility snapshot.

Predictions correspond to `last.pt`, which may differ from `best.pt`. In resumed
runs, the best checkpoint may remain in a parent directory if no improvement occurs.
No original patient images, caches, run predictions or checkpoints are tracked in Git.

After completion:

```powershell
& $python scripts/check_cohort_run.py --run experiments/dwi-cohort-001
& $python scripts/preview_cohort.py --run experiments/dwi-cohort-001 --manifest experiments/isles-curated-001/manifest.json --splits experiments/isles-curated-001/frozen-splits-v1.json --cache data/preprocessing-cache
```

The coverage check verifies every expected training/validation visit and every
final prediction file. The preview shows lowest, middle-ranked and highest Dice
examples; its selected slices are not a substitute for full-volume expert review.

## Interpretation limits

This is a short native-spacing, single-sequence baseline. The sites are mixed
across partitions; validation is reused for development/checkpoint selection.
The validation set contains no empty reference masks. Performance must not be
presented as general screening specificity, external-site or clinical evidence.
The previous two-case debug mean Dice is not directly comparable to the full
37-case cohort mean. Track improvement on the same validation cohort across epochs.
