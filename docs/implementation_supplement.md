## 27. Windows 11 laptop implementation profile

This guide was prepared for the project directory D:\NeuroFusion on 5 October 2026. Read-only inspection reported the following hardware; no training benchmark or software installation was performed.

| Component | Observed value | Planning implication |
|---|---|---|
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU | CUDA-capable NVIDIA device; verify access from the selected Python environment |
| Dedicated GPU memory | 8,188 MiB reported by nvidia-smi | Approximately 8 GB; train small 3D models in patches rather than assuming full-volume training fits |
| Driver | 595.97 | Observed driver version, not a tested dependency combination |
| CPU | Intel Core i7-13700HX | Use CPU preprocessing carefully alongside GPU work |
| System RAM | 16,939,749,376 bytes, approximately 15.8 GiB | Avoid caching an entire volumetric dataset in RAM |
| Operating system | Windows 11, user supplied | Native Windows first; WSL2 is an optional future route |

Use one training or inference workload on the GPU initially. Close other GPU-heavy workloads and keep the laptop on an appropriate power supply with adequate ventilation. Monitor memory and temperature during a short benchmark instead of predicting throughput from the GPU name. GPU memory shared from system RAM is not a substitute for dedicated VRAM in the training plan.

The full platform is feasible as a sequence of experiments; this laptop should not be assumed to train every proposed model concurrently. Start with a narrow 3D U-Net and a small patch. A transformer, large ensemble, or separate-encoder fusion network may require smaller patches, sequential execution, or external compute.

Keep the PDF and editable guide at the project path. Store raw scans under a configurable data root and keep them out of Git. Measure archive size, extracted size, derived-cache size and checkpoint growth before downloading another dataset.

## 28. Environment setup and first GPU checks

These are instructions for future implementation. The PDF generation process did not install project dependencies or execute these setup commands.

### Native Windows route

Use a dedicated Python environment. Python 3.11 is a proposed compatibility starting point, subject to the selected stable PyTorch and MONAI releases supporting it. Check those releases before creating the final lockfile. Do not mix a Windows environment with WSL paths or packages.

```powershell
Set-Location 'D:\NeuroFusion'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Next, obtain the Windows/Pip/CUDA installation command from the official PyTorch selector, selecting a supported combination for the driver and Python environment. Run that command using .venv\Scripts\python.exe -m pip rather than a global pip. This guide deliberately does not invent a fixed CUDA wheel URL. The CUDA version displayed by nvidia-smi is not proof of which runtime a Python environment uses [19].

Install the initial project packages only after PyTorch is confirmed:

```powershell
.\.venv\Scripts\python.exe -m pip install monai nibabel SimpleITK
.\.venv\Scripts\python.exe -m pip install numpy pandas scikit-learn
.\.venv\Scripts\python.exe -m pip install tensorboard pyyaml pytest
```

Freeze a tested set of versions after the first smoke test. Add FastAPI, the selected queue, database dependencies, EEG libraries and viewer integration when their stage begins. Avoid installing all possible model frameworks at once.

GPU smoke test:

```powershell
@'
import torch
print(torch.__version__)
print(torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
'@ | .\.venv\Scripts\python.exe -
```

If the result is false, resolve the environment, wheel and driver mismatch before training. Do not automatically reinstall a working driver or install a separate CUDA toolkit without understanding the selected package requirements.

### Optional WSL2 route

Use WSL2 later if Linux-specific dependencies or GPU containers require it. NVIDIA's WSL guide explains the Windows driver bridge and cautions against installing a Linux display driver inside WSL [20]. Create a separate Linux environment and benchmark filesystem access; do not reuse the Windows .venv. WSL2 setup is a deliberate infrastructure task, not a prerequisite for the first native Windows baseline.

### Windows process handling

Training entry points should use an if __name__ == '__main__' guard. Begin with zero data-loader workers while debugging, then benchmark one or two. Avoid launching many workers on a 16 GB system. Log worker crashes and data-loading time separately from GPU time.

## 29. First training recipe for the local GPU

Default first experiment: ISLES 2022 stroke-lesion segmentation. This experiment studies segmentation on a selected stroke dataset; it does not establish population screening performance. ISLES contains very few no-infarct examples, so robust general screening specificity requires additional appropriate negative cases [5].

### Dataset and partition preparation

1. Download the official available training release after recording its terms.
2. Inventory complete DWI, ADC, FLAIR and mask sets.
3. Verify patient identifiers, geometry, label values and image-mask alignment.
4. Partition by patient. An illustrative 70/15/15 development split of 250 cases is 175/37/38; adapt it to site and lesion distribution and document the choice.
5. Run leakage checks and freeze the split. This internal holdout is not the official ISLES test set.
6. Learn any fitted preprocessing statistics from the training partition only.

### Proposed starting configuration

The values below are engineering starting points, not validated best settings or a guarantee of fitting in 8 GB VRAM.

```yaml
task: isles_stroke_segmentation
seed: 42
inputs: [dwi, adc, flair]
baseline: compact_3d_unet
patch_size: [64, 64, 64]
batch_size: 1
gradient_accumulation: 4
precision: mixed
num_workers: 0
cache: disk_or_small_bounded_cache
optimizer: adamw
learning_rate: 0.0001
loss: dice_plus_cross_entropy
validation: full_volume_sliding_window
sliding_window_batch: 1
checkpoint_selection: validation_metric_only
```

Begin with a single-sequence baseline before the three-input run. Define class channels and the loss implementation consistently; binary versus multiclass targets require compatible output activation and loss settings. Sample both lesion-containing and background patches to address imbalance, but evaluate full studies with their original lesion prevalence.

### Training milestones

| Milestone | Run | Expected evidence |
|---|---|---|
| Pipeline debug | One to two cases and a few steps | Correct tensor shapes, finite loss, visible alignment |
| Tiny-set overfit | A small fixed subset | Model can fit the subset; this is debugging, not accuracy evidence |
| Throughput benchmark | Short representative run | Peak VRAM, RAM, steps/second, validation time |
| Single-sequence baseline | Planned training budget | Saved model and held-out validation curves |
| Early fusion | Same split and comparable budget | Incremental value of DWI/ADC/FLAIR inputs |
| Feature fusion | Small separate encoders | Benefit and cost compared with channel stacking |
| Frozen evaluation | Untouched internal holdout | Patient-level results, failures and uncertainty |

Compare multiple seeds if resources permit. If only one seed is feasible, say so. Hyperparameter exploration consumes validation data; repeated tuning on the test partition invalidates its independence.

### Memory fallback ladder

If CUDA runs out of memory, stop the failed run cleanly and record the configuration. Reduce patch dimensions or network width, keep batch size one, use supported mixed precision, and benchmark activation checkpointing if needed. Gradient accumulation increases effective batch size but does not shrink the memory required for one patch. Do not use class-changing crops or destroy lesion visibility merely to fit memory.

For validation, process a full volume with sliding windows and stitch predictions before calculating full-study metrics. MONAI provides controls for window size, overlap, patch batch size and compute/output devices [21]. Benchmark CPU output accumulation because it can reduce GPU pressure while increasing system RAM usage.

## 30. Model inventory and training contracts

The earlier estimate of 12 specialist models was a grouping, not a final checkpoint count. For planning, use 15 separately evaluated learned task modules below. Baselines, fusion variants, ensembles and dataset-specific versions can increase the number of trained checkpoints. Anatomy measurement and RAG add supporting models.

| ID | Task module | Training contract | Evaluation focus |
|---|---|---|---|
| M01 | Glioma-region segmentation | Compatible BraTS sequences and voxel masks; compact 3D U-Net baseline | Region Dice, boundary error and volume error |
| M02 | 2D tumor category prediction | BRISC images with four labels; transfer-learning CNN | Class sensitivity, confusion and disclosed identity limitations |
| M03 | Metastasis segmentation | BraTS-METS release-specific sequences and masks | Small-lesion sensitivity and false positives |
| M04 | Pediatric tumor segmentation | BraTS-PEDs population-specific masks | Age/population scope and region performance |
| M05 | Acute/subacute stroke lesions | ISLES DWI/ADC/FLAIR with lesion masks | Lesion-level sensitivity, Dice, volume error |
| M06 | Established stroke lesions | ATLAS T1 volumes and masks | Chronicity/site-stratified performance |
| M07 | CT hemorrhage prediction | RSNA image labels, study-aware aggregation | Study and slice metrics reported separately |
| M08 | Aneurysm candidates | RSNA task-compatible images and location labels | Location sensitivity and false positives |
| M09 | White matter hyperintensities | WMH T1/FLAIR with masks | Lesion burden, lesion-level detection and Dice |
| M10 | Cerebral microbleeds | VALDO task-specific MRI and masks | Lesion detection with false positives per case |
| M11 | Lacunes | VALDO task-specific MRI and labels | Lesion sensitivity, label uncertainty |
| M12 | New MS lesions | Same-patient follow-up scans and new-lesion masks | Temporal matching and new-lesion detection |
| M13 | EEG seizure events | TUSZ/CHB-MIT event annotations; temporal CNN baseline | False alarms/hour, event sensitivity, latency |
| M14 | CT structural finding flags | CQ500 labels; development cohort still required | Per-label performance, no unsupported measurements |
| M15 | Defined Alzheimer-related endpoint | ADNI matched visits and chosen reference endpoint | Leakage-controlled endpoint prediction and calibration |

M14 and M15 are data-dependent research modules. They are not ready merely because a dataset name is known. Use image-level labels only for image-level objectives; training a segmentation model requires spatial supervision or a separately evaluated weak-supervision method.

Supporting components:

- Anatomical segmentation for region descriptions and measurements; validate reference labels and alignment before use.
- Optional enlarged-perivascular-space segmentation; this imaging marker is not itself a universal danger label.
- Quality checks based on metadata and rules initially. Learned artifact detection requires quality annotations.
- Calibration models fitted only on validation outputs.
- An embedding model, reranker and language model for the literature assistant, independently evaluated for report faithfulness.

### Recipe adaptations

For CT hemorrhage, use a 2D or 2.5D baseline on the local GPU, then aggregate ordered slices. Do not train on slice labels and report unvalidated patient-level decisions. For EEG, fit normalization on training recordings, split by subject before windowing, and fix event-matching tolerance before scoring. CHB-MIT does not automatically match the TUSZ montage or population.

For M15, select one endpoint and prediction time before designing fusion. Do not feed a diagnostic label, post-outcome measurement, or future visit into the predictor. Matched MRI, PET and clinical records may be missing; missingness can encode site/cohort information and must be audited.

## 31. Detailed file responsibilities and data lifecycle

Use one Python package layout during implementation rather than mixing multiple competing layouts from early planning. The recommended expanded target is:

```text
D:\NeuroFusion\
  NeuroFusion_Full_Project_Guide.pdf
  README.md
  pyproject.toml
  requirements.lock.txt
  .env.example
  .gitignore
  backend/app/                   API, schemas, permissions, jobs
  frontend/                      Web routes and viewer components
  src/neurofusion/
    io/                          DICOM, NIfTI and EEG readers
    preprocessing/               Geometry and signal transforms
    registration/                Alignment and transform records
    measurements/                Physical-unit measurements
    models/                      Specialist architectures
    fusion/                      Early, feature and temporal fusion
    inference/                   Capability routing and execution
    provenance/                  Artifact and finding references
    review/                      Annotation state transitions
    active_learning/             Selection and approved-label export
    reporting/                   Structured reports and RAG
    federated/                   Coordinator and clients
  datasets/
    adapters/                    Dataset-specific import logic
    manifests/                   Versioned file/label inventories
    splits/                      Patient partition definitions
    leakage/                     Duplicate and overlap audits
  training/                      Training runners and callbacks
  evaluation/                    Metrics, calibration, test suites
  workers/                       Background task entry points
  configs/                       Versioned experiment settings
  scripts/                       Data audits and operational tools
  tests/                         Focused unit and integration checks
  docs/                          Manual, sources and model cards
  artifacts/                     Ignored model outputs and logs
  data/                          Ignored raw and derived data
```

Only the guide artifacts are delivered now; this tree specifies the future implementation. Do not mistake listed scripts for existing commands.

| Proposed file | Responsibility | Essential test |
|---|---|---|
| datasets/adapters/isles.py | Resolve sequences, masks and patient identity | Missing pairs and corrupt files are reported |
| scripts/audit_dataset.py | Build manifest, class counts and geometry summary | Deterministic manifest and invalid-label checks |
| datasets/leakage/audit.py | Hash and patient overlap analysis | Seeded duplicates block unsafe split reuse |
| src/neurofusion/preprocessing/mri.py | Reversible geometry-aware transforms | Image/mask alignment and inverse-transform test |
| training/train_segmentation.py | Load config, train, checkpoint and resume | Resume preserves optimizer and experiment state |
| evaluation/evaluate_segmentation.py | Full-study and lesion metrics | Empty masks and missed lesions handled explicitly |
| src/neurofusion/inference/registry.py | Model input contracts and versions | Unsupported modality is rejected |
| src/neurofusion/inference/router.py | Select compatible analyses | Missing sequence produces not_assessed |
| src/neurofusion/provenance/evidence.py | Link findings to source coordinates | Resampling does not break viewer location |
| src/neurofusion/review/workflow.py | Independent review and adjudication | Conflicting edits create revisions, not overwrites |
| src/neurofusion/reporting/build.py | Produce template-based research reports | Values match structured findings |
| src/neurofusion/federated/simulate.py | Run a reproducible client experiment | Interrupted client recovery and no raw-data transfer |

### Data lifecycle

Immutable raw files become checked manifests, then versioned derived data, then training examples. Approved checkpoints produce predictions linked to their exact inputs and preprocessing. Reviewer revisions are separate artifacts. An approved label export may enter a new dataset version; previous reports and model outputs remain traceable.

The metadata database should represent studies, series, datasets, partitions, models, experiments, jobs, findings, evidence references, annotations, reviews and reports. Large binary scans belong in artifact storage, not database rows. Use access checks for every artifact reference.

## 32. Build roadmap with stages and exit evidence

The estimates below are planning allowances for one developer with working Python skills, not commitments. Dataset approvals, annotation access, coursework and failed experiments can dominate calendar time. A credible first specialist and web demo may take months; the full portfolio is a longer research program.

| Phase | Stages | Deliverables | Planning allowance |
|---|---|---|---|
| A. Foundation | A1 scope; A2 GPU environment; A3 dataset access; A4 manifests/leakage | Environment record, selected task and frozen partitions | 1-2 focused weeks after access |
| B. First specialist | B1 geometry; B2 debug; B3 benchmark; B4 baseline | Reproducible training and evaluation report | 2-4 focused weeks |
| C. Fusion research | C1 single inputs; C2 early fusion; C3 feature fusion; C4 robustness | Controlled experiment and limitations | 2-4 focused weeks |
| D. Web product | D1 jobs; D2 viewer; D3 evidence links; D4 reports | One complete research workflow | 3-5 focused weeks, partly parallel with C |
| E. Reviewed learning | E1 independent review; E2 adjudication; E3 active learning | Approved-label cycle and comparison | 2-4 focused weeks with reviewer access |
| F. Imaging expansion | F1 second MRI branch; F2 CT; F3 vascular/small lesions | Per-module model cards and benchmarks | Re-estimate each task after audit |
| G. Temporal and signals | G1 longitudinal; G2 EEG; G3 ADNI endpoint | Separate paired-data and signal evaluations | Re-estimate from cohort availability |
| H. Federation | H1 local baselines; H2 simulated clients; H3 failures/privacy review | Federated comparison report | Several focused weeks after mature baseline |
| I. Release | I1 regression; I2 docs/demo; I3 server deployment | Reproducible web release and rollback artifacts | Depends on chosen hosting and access controls |

### Phase A exit gate

CUDA is available in the project environment; a complete study can be loaded with correct geometry; provenance and dataset terms are recorded; patient partition audits pass or limitations are documented. No public-data availability assumption remains hidden.

### Phase B exit gate

Tiny-set debugging passes; full-volume validation runs within measured resource limits; checkpoints resume; an untouched holdout exists; a failure review identifies missed lesions and false positives. Baseline quality is measured, not described as excellent without evidence.

### Phase C exit gate

Fusion is compared against single-sequence and channel-stacking baselines. Geometry perturbations are scored correctly. Missing sequences have tested behavior. Select the simplest configuration that meets the predefined research objective.

### Phase D exit gate

An authorized user uploads a de-identified study, sees compatible modules, submits a job, views evidence-linked findings and exports a faithful report. Corrupt inputs, worker failure, cancellation and GPU memory errors have readable outcomes.

### Phases E-H exit gates

New labels are independently reviewed; active-learning gains are compared with random selection; every added specialist has its own evaluation; longitudinal studies are correctly matched; EEG is evaluated by events; federated results are compared with local and centralized baselines. These gates cannot be satisfied by a visually polished dashboard alone.

### Phase I exit gate

Rebuild from documented dependencies, verify model checksums, rerun regression fixtures, review privacy/access controls, publish permitted code and demo data, and record known limitations. Publishing a research release does not imply clinical readiness.

## 33. First ten working sessions

1. Read the coverage matrix, select ISLES, and record an explicit research question and intended population.
2. Set up the isolated environment and execute the GPU smoke test. Record versions without installing unrelated frameworks.
3. Obtain the permitted training data and record checksums, labels and metadata limitations.
4. Open representative studies and masks. Check DWI/ADC/FLAIR pairing, orientation and spatial alignment.
5. Implement the manifest and patient partitions; run leakage checks before extracting patches.
6. Implement a preprocessing round trip and visualize the transformed masks.
7. Build a compact baseline and run a tiny-set overfit check.
8. Measure VRAM, RAM, throughput and full-volume validation. Choose a feasible patch/network configuration.
9. Run a reproducible baseline, save checkpoints and inspect errors on validation cases.
10. Start the first fusion comparison and sketch the web workflow using genuine held-out sample outputs.

Do not spend these sessions downloading all datasets or creating a large empty folder tree. The outcome should be one verified data-to-prediction loop that can become the foundation of the whole platform.

## 34. Experiment records and acceptance templates

### Experiment card

```yaml
experiment_id: stroke_baseline_001
question: Does the proposed input improve held-out segmentation?
dataset_version: recorded_release_and_checksum
split_manifest: immutable_partition_reference
preprocessing_version: git_commit_or_package_version
model_config: versioned_yaml_reference
seeds: [42]
training_budget: defined_before_comparison
checkpoint_rule: validation_only
primary_metric: predeclared_task_metric
secondary_metrics: [lesion_sensitivity, false_positives, runtime]
hardware: RTX_4070_Laptop_8GB
status: planned
```

### Model card checklist

State intended task, excluded uses, training population, inputs, labels, preprocessing, limitations, partitions, overlap audits, metrics with confidence intervals, threshold selection, calibration, hardware, model checksum, dependencies and examples of failure. Distinguish internal validation from independent external evaluation.

### Weekly review

Answer five questions: What can be demonstrated? What is measured? What failed? What data or hardware constraint blocks progress? What single experiment or implementation step resolves the next uncertainty? Update the capability registry rather than claiming a percentage complete across incomparable disease modules.

## 35. Troubleshooting guide

| Symptom | Likely investigation | Correct next action |
|---|---|---|
| CUDA unavailable | Wrong wheel/environment or driver mismatch | Verify interpreter and official supported installation combination |
| GPU memory exhausted | Patch, width, precision or overlapping jobs | Apply the memory fallback ladder; preserve failed config |
| System memory exhausted | Volume cache, workers or CPU output accumulation | Bound cache, reduce workers, measure peak RAM |
| Loss is NaN | Labels, normalization, learning rate or precision instability | Inspect one batch and full-precision debug run |
| Mask looks shifted or flipped | Orientation, registration or inverse transform | Repair geometry before interpreting model metrics |
| High validation score, poor new-site performance | Leakage, cohort shift or preprocessing mismatch | Audit independence and external protocol compatibility |
| Tiny lesions disappear | Resampling, crop sampling or class imbalance | Review lesion visibility and lesion-level metrics |
| EEG false alarms dominate | Artifacts, montage or event postprocessing | Inspect false alarms and validate event thresholds |
| Good fusion reward but little clinical-task gain | Metric or experiment mismatch | Compare the same held-out task metrics and costs |
| Reports disagree with viewer | Stale artifact or revision references | Trace model/mask versions through evidence links |
| API healthy, no predictions | Worker/model readiness failure | Separate service health from inference readiness |

Do not respond to unexplained poor results by adding more models. First verify the labels, task definition, geometry, partitions and evaluation code.

## 36. Web deployment and GitHub publishing

The agreed product is a website, with no Windows executable. During development the frontend opens in a browser and the backend runs on the laptop. A public online analysis service requires its own operational backend; publishing source code does not make GPU inference available to visitors.

| Component | Development | Published research release |
|---|---|---|
| Source and guide | D:\NeuroFusion and Git | GitHub repository |
| Frontend | Local web development server | Suitable web hosting |
| Inference | Local GPU worker | Authenticated server/worker with measured capacity |
| Documentation/demo | Local sample outputs | Static site with permitted de-identified examples |
| Large weights | Local artifact directory | Licensed artifact hosting with checksums |
| Sensitive studies | Controlled local storage | Access-controlled storage, never a public repository |

GitHub Pages hosts static files and cannot execute the Python inference backend [22]. A useful first public deliverable is a static showcase with precomputed results, clearly labeled as a demo. Live inference can follow after authentication, quotas, job isolation, upload validation, artifact access controls and operational monitoring are ready.

Use CI to lint code, run small fixture tests, validate schemas and build the frontend. Do not launch full GPU training on every commit. Model promotion should require a frozen evaluation report and model-card review. Keep a known-good model artifact for rollback; this operational requirement supports the existing research release process.

## 37. Boundaries and unresolved decisions

Before implementation, settle the first dataset's access, exact Python/PyTorch/MONAI combination, available disk budget, annotation collaborator availability, and time commitment. Before online inference, choose hosting, retention rules and data access controls. Before learned cross-disease fusion, obtain a suitable same-patient cohort.

All requested high-priority additions and the advanced federation experiment are included in the roadmap. Medium-priority suggestions such as educational mode and similar-case search remain optional, not required for the first release. Established features such as model versioning, traceable reporting and subgroup error analysis remain part of baseline engineering and evaluation.

This guide describes how to build a broad research platform; it does not promise detection of every neurological condition. Negative findings apply only to the model's validated target and input. Clinical interpretation and any real patient use require appropriately qualified oversight and validation beyond the research benchmarks.

## 38. Additional implementation references and glossary

19. **PyTorch installation selector:** choose a supported Windows/Pip/CUDA environment at implementation time. https://pytorch.org/get-started/locally/
20. **NVIDIA CUDA on WSL guide:** Windows driver integration and WSL-specific setup. https://docs.nvidia.com/cuda/wsl-user-guide/index.html
21. **MONAI inference methods:** sliding-window controls and device placement. https://docs.monai.io/en/1.4.0/inferers.html
22. **GitHub Pages:** static hosting scope. https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages

| Term | Meaning in this project |
|---|---|
| MRI sequence | An acquisition producing a particular tissue contrast; sequences are not interchangeable |
| DICOM | Medical image format and associated metadata used in imaging systems |
| NIfTI | A common research format for spatial medical-image volumes |
| Voxel | A three-dimensional image element with physical spacing |
| Segmentation | Assigning region labels to pixels or voxels |
| Registration | Aligning images while retaining the transformation between coordinate spaces |
| Fusion | Combining compatible input information, features or predictions |
| Calibration | Comparing model scores with observed outcomes on suitable evaluation data |
| Abstention | Declining to produce a supported finding when input or reliability requirements fail |
| Leakage | Information shared across development and evaluation that invalidates independence |
| External validation | Evaluation on a genuinely separate, compatible cohort |
| Active learning | Selecting cases for annotation using a defined acquisition strategy |
| Federated learning | Training across clients that exchange updates rather than pooling raw inputs |
| RAG | Retrieving relevant sources before generating a source-grounded explanation |

The PDF, editable source and generator are the outputs of this documentation task. The commands, API routes and scripts described in the implementation plan must still be built and tested.
