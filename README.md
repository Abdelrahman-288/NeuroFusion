> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](docs/RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](docs/CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# NeuroFusion

Research web-platform project for evaluated brain imaging and signal models.
The current implementation includes the **data foundation and a full-cohort
3D segmentation training pipeline**. The first five-epoch DWI baseline is complete:
174 training studies, 37 validation studies, mean validation Dice 0.316. Results
remain uneven and are research-only. A local upload-and-prediction web viewer is implemented.
The original PDF guide is preserved.

Track the expanded roadmap in [implementation status](docs/IMPLEMENTATION_STATUS.md).
See the [progress tracker](docs/PROJECT_PROGRESS.md) and [DWI/ADC fusion readiness](docs/FUSION_READINESS.md).
The [first full fusion comparison](docs/FUSION_EXPERIMENT.md) is complete; DWI-only remains the stronger development baseline.
The second dataset, [BRISC v6](docs/BRISC_DATASET.md), now has a [four-class tumor classifier](docs/TUMOR_BASELINE.md) and a [2D tumor segmenter](docs/TUMOR_SEGMENTATION.md). The segmenter reached mean original-size validation Dice 0.6699. Use the [local prediction viewer](docs/LOCAL_VIEWER.md) for uploads, independent model outputs and interactive overlays. [Background jobs and saved-result history](docs/BACKGROUND_JOBS.md) now persist locally across page reloads and server restarts. [Human review notes](docs/HUMAN_REVIEW.md) can be saved separately and linked to displayed slices. [Research reports](docs/RESEARCH_REPORTS.md) export predictions, provenance, previews and reviewer observations to offline HTML or JSON. [Technical input checks](docs/INPUT_QUALITY.md) now reject unusable files before inference and record compatibility warnings.
For the implemented download, preprocessing and GPU debugging workflow, see
[next milestone](docs/NEXT_MILESTONE.md). A synthetic training curve is available
locally at `experiments/synthetic-overfit-001/progress.html`.
Current results and commands: [cohort training](docs/COHORT_TRAINING.md).
Latest evaluation: [lesion analysis and next experiment](docs/LESION_ANALYSIS.md).
Sampling comparison: [component-balanced experiment](docs/COMPONENT_SAMPLING_EXPERIMENT.md).
Local error dashboard: `experiments/lesion-analysis-001/index.html`.
Latest training history: `experiments/dwi-cohort-001/progress.html`.
Earlier debugging experiments: [baseline run](docs/BASELINE_RUN.md).

## Start here (PowerShell)

```powershell
Set-Location D:\NeuroFusion
$python = '.\.venv-neurofusion\Scripts\python.exe'
& $python -m neurofusion --help
& $python -m pytest -q
& $python -m neurofusion doctor --require-cuda --output experiments\my-gpu-check.json
& $python -m neurofusion demo --output experiments\my-synthetic-demo
```

Every output must be a new path. This protects previous runs. The demo generates
12 tiny synthetic patients and exercises NIfTI validation, manifests, splitting
and leakage auditing. It **does not train or evaluate a medical model**.

## Implemented

- Installable Python package and command-line entry point.
- GPU diagnostics with a real 3D convolution forward/backward computation.
- Explicit CSV study indexing and streamed file checksums.
- 3D NIfTI shape, finite-value, nonconstant-image and binary-mask checks.
- Spatial affine validation, DWI-mask grid matching and sequence-geometry warnings.
- Deterministic patient-level partitions and exact decoded-image duplicate checks.
- Saved JSON evidence and tests for corruption, leakage and invalid partitions.

## Real dataset workflow

Follow [dataset setup](docs/DATASET_SETUP.md). The registry is
`configs/datasets.json`. Real scans are not included.

```powershell
& $python -m neurofusion manifest --index data\isles-index.csv --root data\raw\isles-2022 --dataset-id isles-2022 --output data\isles-manifest.json
& $python -m neurofusion split --manifest data\isles-manifest.json --seed 42 --output data\isles-splits.json
& $python -m neurofusion audit --manifest data\isles-manifest.json --splits data\isles-splits.json --output experiments\isles-audit.json
```

The splitter blocks detected identity/duplicate errors. Geometry warnings need
review before training. A passing audit checks declared identities and exact
content only; it does not establish dataset independence or clinical validity.
Rebuild manifests after files change. Treat manifests as private data artifacts.

## Recreate the environment

Python 3.11 was selected for this foundation. The separate `.venv-neurofusion`
does not inherit global packages; the pre-existing `.venv` is preserved.

```powershell
py -3.11 -m venv .venv-neurofusion
& .\.venv-neurofusion\Scripts\python.exe -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
& .\.venv-neurofusion\Scripts\python.exe -m pip install -e '.[dev]'
```

This is a deliberately pinned foundation, not a claim to use the newest release.
Official PyTorch installation reference: https://pytorch.org/get-started/locally/.
Use the saved environment snapshot after verification for exact package versions.

For this laptop, the working `2.5.1+cu121` distribution and supporting packages
were copied from the existing local Python installation into the isolated venv
to avoid a stalled multi-gigabyte download. Global packages were not modified.
`experiments/local-package-bootstrap.json` records the provenance. The environment
does not use global-site-package inheritance. Recreating it with official wheels
using the commands above is the preferred portable installation route.

## Layout

```text
configs/                  Dataset registry and study-index schema
src/neurofusion/           CLI, image QC, splitting, auditing, GPU diagnostics
tests/                    Data-integrity and CLI regression tests
data/                     Local scans and private manifests (ignored)
experiments/              Local run evidence and checkpoints (ignored)
docs/                     Guide, dataset instructions, implementation status
```

Real ISLES preparation is now complete through automated auditing: 250 studies
downloaded, two duplicate-content subjects quarantined, and 248 retained in draft
partitions. See [data findings](docs/DATA_QC_FINDINGS.md). DWI preprocessing has
passed a real-study roundtrip, and a synthetic GPU overfit check has passed.
The initial partitions are now frozen after distribution review. The compact
DWI U-Net completed small real-data runs and exact checkpoint-resume verification.
Fixed real-training-patch overfit passed (training Dice 1.0; not generalization).
Full-cohort training now works with bounded memory and complete validation coverage.
The component-balanced sampler improved validation mean Dice to 0.361 and lesion
recall to 24.6%; false positives remain. Next: reduce false positives, repeat with
additional seeds, and test ADC fusion while keeping the holdout unused.
Later releases expand fusion, review workflows and further specialists.

The [first robustness evaluation](docs/ROBUSTNESS_EVALUATION.md) measured substantial sensitivity to a controlled contrast change (82.82% to 51.11% validation accuracy). No model was replaced.

The [segmentation robustness extension](docs/SEGMENTATION_ROBUSTNESS.md) evaluates all 721 tumor validation images and 37 stroke validation volumes under six conditions each. Saved predictions support exact metric replay. Blur lowers mean Dice from 0.670 to 0.579 for tumor segmentation and from 0.361 to 0.306 for stroke. Testing is complete; these failures do not establish robustness or qualify a model for promotion.

The [controlled augmentation experiment](docs/AUGMENTATION_EXPERIMENT.md) improves contrast-test accuracy to 82.29%, with clean accuracy 82.08%. The viewer continues using the original checkpoint pending broader evaluation.

The [three-seed evaluation](docs/MULTISEED_EVALUATION.md) confirms contrast gains but rejects the current augmentation policy under development screening criteria because of clean/per-class regressions. The viewer model remains unchanged.

The [contrast-only three-seed experiment](docs/CONTRAST_EXPERIMENT.md) passes the development screen with smaller clean losses, while retaining darker-image and meningioma-recall weaknesses. Independent evaluation is required; the viewer model is unchanged.

The [external dataset readiness stage](docs/EXTERNAL_DATA_READINESS.md) adds a checksum-backed overlap audit, patient-level flag propagation and source-lineage review. Positive controls were detected against all 6,000 BRISC images. External cohort acquisition and model scoring remain pending.

The [UCSF-PDGM metadata intake](docs/PDGM_INTAKE.md) adds 501 exam records grouped into 495 patients, BraTS cross-references, a deterministic import pilot and tested volume intake checks. The [first real MRI/mask import](docs/PDGM_FIRST_IMPORT.md) is now complete: one of 20 pilot exams, 155 prepared slices and a documented resizing warning. No external scans have been scored.

The [external volume adapter](docs/EXTERNAL_ADAPTER.md) prepares canonical slices with physical-aspect padding and restores probability arrays to native coordinates. Synthetic verification passed; real MRI alignment, label semantics and external evaluation remain pending.

The [external pilot importer](docs/EXTERNAL_IMPORT.md) validates explicit patient/file mappings and checksums, prepares each available exam and reports failures/missing files. One synthetic control passed; all 20 real pilot exams await image acquisition.

The [confidence calibration experiment](docs/CALIBRATION_EXPERIMENT.md) tested a scalar temperature on separate development groups. Confidence metrics worsened across clean and perturbed evaluation images, so the calibrator was rejected and the viewer is unchanged.

The [real-volume resolution audit](docs/PDGM_RESOLUTION_AUDIT.md) quantifies small annotation-component loss and records the native-mask scoring policy.

Latest [UCSF pilot milestone](docs/PDGM_PILOT_COMPLETE.md): all 20/20 exams imported, 3,100 slices and zero failures. Label/alignment review and external evaluation remain pending.

[Full pilot resolution QA](docs/PDGM_PILOT_RESOLUTION.md): 20 exams at three sizes, 155 tests passed; model inputs unchanged.

[Candidate target contract](docs/PDGM_TARGET_CONTRACT.md): source evidence, 20-mask numeric-region inventory and current-model compatibility limitations.

[Alignment review gallery](docs/PDGM_ALIGNMENT_GALLERY.md): 180 original-grid views across all 20 pilot exams; expert reviews remain pending.

[Patient/source separation inventory](docs/PDGM_COHORT_SEPARATION.md): patient-level pilot exclusions, BraTS cross-references and a non-frozen 192-patient candidate pool.

[Native-grid metrics](docs/NATIVE_METRICS.md): explicit geometry/empty-mask policies; synthetic verification only.
