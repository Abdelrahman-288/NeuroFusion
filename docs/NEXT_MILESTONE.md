> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# Data preparation and first debugging run

Updated 2026-10-06. The implementation now includes a resumable, checksum-verified
downloader for the public ISLES 2022 v2.3.1 release, a strict indexer, per-study
auditing, local image previews, reversible DWI preprocessing, and a GPU synthetic
overfit check. Dataset source: https://zenodo.org/records/7960856.
The release API reports open access with CC-BY-4.0 attribution requirements.
Download metadata and provenance stay under `data/downloads/isles-2022-v2.3.1/`.

The real-data run is complete. See `DATA_QC_FINDINGS.md`: the original 250-study
audit found a duplicate-content pair, both subjects were quarantined, and the
248-study curated audit passes. The commands below are examples for fresh runs;
existing outputs must be inspected or a new run number selected. The original
uncurated manifest must not be used directly for training.

## Run the data pipeline

From `D:\NeuroFusion` in PowerShell, use the isolated project Python:

```powershell
$python = '.\.venv-neurofusion\Scripts\python.exe'
& $python scripts/download_isles.py
& $python scripts/index_isles.py --root data/raw/isles-2022 --output data/isles-index.csv
& $python scripts/audit_isles.py --index data/isles-index.csv --root data/raw/isles-2022 --dataset-id isles-2022-v2.3.1 --output experiments/isles-qc-001
& $python scripts/preview_studies.py --manifest experiments/isles-qc-001/manifest.json --output experiments/isles-preview-001
```

The downloader resumes interrupted transfers and verifies both publisher MD5
and local SHA256 before extraction. Do not run two downloaders against the same
directory. The extractor rejects paths outside its output root and symbolic links.
Other tools require fresh output paths. When a run already exists, inspect it or
choose a new run number. The indexer recognizes source BIDS-style subject/session
identifiers and rejects ambiguous sequence matches.

The full-cohort audit records invalid cases rather than silently dropping them.
Draft partitions are only produced when every indexed case and leakage checks
pass. Site and lesion distributions still need review before partitions are frozen.
Visual previews show supplied annotations, not predictions, and cannot replace
full-volume inspection. The archive's center metadata is preserved for later
site-aware evaluation design.

## DWI preprocessing

```powershell
& $python scripts/preprocess_study.py --dwi PATH_TO_DWI --mask PATH_TO_MASK --output experiments/prepared-study-001
```

This first baseline uses DWI alone. It applies RAS axis permutations/flips and
per-image nonzero intensity normalization. It saves an inverse orientation and
original affine so model outputs can be mapped back to the original grid. It
does not perform interpolation, registration or spacing normalization. ISLES
FLAIR is not preregistered; do not stack it with DWI until registration is built
and inspected. Matching array dimensions alone do not establish registration.

## Inspect the completed synthetic debugging run

`experiments/synthetic-overfit-001/progress.html` displays the loss curve.
The run used 200 GPU steps on one artificial study. Training Dice reached 1.0;
this is a deliberately easy memorization check, not held-out accuracy. Artifacts:

- `history.csv`: step, loss and training Dice.
- `debug-checkpoint.pt`: model/optimizer state, step, seed and architecture.
- `probability-native.nii.gz`: probabilities mapped to the original grid.
- `report.json`: measured runtime, memory use and limitations.

Repeat with a new run directory:

```powershell
& $python scripts/train_debug.py --output experiments/synthetic-overfit-002 --steps 200
```

This compact convolutional debugging model is not the planned specialist U-Net.
It does not implement a real-data training/evaluation runner, checkpoint resume,
or holdout evaluation. Those follow real-data inspection and partition approval.
