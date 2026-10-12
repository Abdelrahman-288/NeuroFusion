> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](docs/CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# NeuroFusion Project Manual

Current scope amendment, 10 October 2026: mandatory expert review was removed at the user's explicit request. Expert review is optional for this research project. Earlier requirements for expert sign-off in this preserved design manual are superseded by `docs/SCOPE_FREEZE.md` and `docs/research_qualification.json`. Automated data checks, independent evaluation and model-performance checks remain required; no clinical qualification is implied.

Version 1.1 | 5 October 2026

Status: proposed research architecture and implementation guide. No NeuroFusion models, application, or clinical capability have been implemented or validated by creating this manual.

## 1. Purpose and intended outcome

NeuroFusion is a proposed research platform for analyzing selected neurological abnormalities using specialist models for MRI, CT, angiographic imaging, and EEG. It combines compatible information from the same examination, displays model findings with uncertainty, and supports human review.

The objective is broad, measurable coverage of supported findings, rather than a universal detector of every brain disease. A growing collection of models cannot establish comprehensive coverage: each finding requires appropriate inputs, reliable labels, independent evaluation, and a defined population.

The primary users of the research prototype are its developers, imaging researchers, and qualified clinical collaborators. Outputs are research findings, not independent diagnoses, treatment recommendations, clearance that a brain is healthy, or predictions of imminent harm.

The first complete release should analyze one volumetric MRI task, compare fusion methods, display editable lesion masks, calculate validated measurements, and export reproducible results. Subsequent releases add independently evaluated specialist modules.

Delivery format: a browser-based application, developed locally and later deployable to a server. Windows executable packaging is outside the agreed scope. GitHub hosts source and documentation; the full online application requires backend hosting for inference.

Version 1.1 adds six high-priority features and one advanced feature to the required roadmap: active learning, finding-to-evidence links, collaborative review, dataset leakage detection, a fusion experiment lab, robustness testing, and federated-learning experiments. Their specifications and acceptance gates are in Section 26. These are planned requirements, not implemented capabilities.

## 2. How to use this manual

1. Read the coverage matrix and select the first clinical research task.
2. Confirm computing resources and dataset access before choosing model sizes.
3. Complete the dataset audit and freeze patient-level partitions.
4. Build a baseline and evaluation pipeline before advanced fusion.
5. Follow the release gates; do not activate a module merely because training finishes.
6. Keep a capability registry so the interface exposes only validated input-task combinations.

All architecture and model choices below are proposals. Dataset facts are linked to primary sources in Section 25. Access conditions, available labels, and releases must be checked again when downloading.

## 3. Capability status definitions

| Status | Meaning |
|---|---|
| Planned core | A task with an identified dataset and a reasonably defined experiment; not yet implemented |
| Planned extension | A candidate task requiring additional engineering, access checks, or label audits |
| Data-dependent | A desired feature without a verified, sufficient training and evaluation cohort |
| Not supported | A finding or use outside the activated model's validated scope |
| Research validated | Passed the project's documented research acceptance criteria; this does not mean clinically approved |

Every module must declare its population, modality, sequence requirements, target labels, output level, evaluation results, and failure conditions.

## 4. Expanded abnormality and data coverage matrix

The following entries are overlapping clinical or imaging categories, not an exhaustive list of brain diseases. They must not be counted as independent diseases to inflate coverage.

| Target | Required input | Proposed dataset | Proposed output | Scope |
|---|---|---|---|---|
| Glioma-related tumor regions | T1, contrast-enhanced T1, T2, FLAIR MRI according to the selected release | BraTS [1] | Region masks, lesion extent and volume | Planned core |
| Selected tumor image categories | Supported 2D contrast-enhanced T1 images | BRISC [2] | Glioma, meningioma, pituitary tumor, non-tumorous class scores | Planned extension; separate 2D experiment |
| Brain metastases | Matched MRI sequences defined by the release | BraTS-METS [3] | Candidate metastatic-lesion masks and counts | Planned extension |
| Pediatric tumor regions | Supported pediatric MRI | BraTS-PEDs [4] | Tumor segmentation within the dataset's population | Planned extension; separate pediatric evaluation |
| Acute/subacute ischemic stroke lesions | DWI, ADC, FLAIR MRI | ISLES 2022 [5] | Lesion masks, counts and volume | Planned core; recommended first fusion task |
| Established stroke lesions | Supported T1 MRI | ATLAS [6] | Stroke-lesion segmentation | Planned extension; use chronicity metadata |
| Intracranial hemorrhage | Supported non-contrast head CT | RSNA ICH [7] | Presence and hemorrhage subtype scores | Planned core after first MRI release |
| Aneurysm candidates | Compatible CTA, MRA, or MRI protocol | RSNA aneurysm dataset [8] | Candidate presence and location | Planned extension |
| White matter hyperintensities | T1 and FLAIR MRI | WMH challenge [9] | WMH segmentation and burden | Planned extension; not an etiologic diagnosis |
| Cerebral microbleeds | Susceptibility-sensitive MRI according to the release | VALDO task 2 [10] | Candidate microbleed locations and masks | Planned extension |
| Lacunes of presumed vascular origin | Required VALDO task sequences | VALDO task 3 [10] | Candidate lesion locations and segmentation | Planned extension |
| Enlarged perivascular spaces | Required VALDO task sequences | VALDO task 1 [10] | Quantitative imaging-marker segmentation | Optional extension; not inherently a dangerous finding |
| New lesions in multiple sclerosis follow-up | Matched longitudinal MRI, particularly supported FLAIR acquisitions | MSSEG-2 candidate [11] | Candidate new-lesion masks | Planned extension after data access and protocol audit |
| Atrophy patterns and Alzheimer-related research endpoints | Structural MRI, optionally matched PET, cognitive and clinical records | ADNI [12] | Regional measurements and explicitly defined research predictions | Planned extension; not diagnosis from MRI alone |
| Seizure events during recordings | Multichannel scalp EEG | TUH Seizure Corpus and CHB-MIT [13,14] | Event intervals and probabilities | Planned extension; electrical-signal branch |
| CT mass effect, midline shift and skull fracture | Supported head CT | CQ500 [15] | Study-level finding flags where labels exist | Planned extension; small benchmark, additional development data needed |

The hemorrhage branch covers the RSNA labels: intraparenchymal, intraventricular, subarachnoid, subdural, and epidural hemorrhage. A model predicting these labels is not automatically a bleeding segmentation model.

BraTS tumor-related edema/invaded-tissue masks are not labels for all causes of brain swelling. An aneurysm location label does not establish rupture risk. Stroke-lesion segmentation does not independently determine stroke timing, cause, or treatment eligibility. Seizure-event detection does not establish that a person has epilepsy or predict future seizures.

## 5. Additional desired coverage requiring new evidence

Keep the following on a data-dependent backlog, rather than advertising them as detected conditions:

- Hydrocephalus and ventricular enlargement: require suitable positive/negative cohorts and clinical definitions. Ventricular size alone cannot establish the diagnosis.
- Diffuse edema, herniation, and quantitative midline-shift measurement: require appropriate annotations and geometry. Existing image-level flags do not supply measurement supervision.
- Traumatic contusions and diffuse axonal injury: need task-specific CT/MRI cohorts. Hemorrhage or fracture detection does not cover all traumatic brain injury.
- Abscesses, encephalitis, meningitis, and other infections: need appropriate imaging and clinical or laboratory reference standards.
- Arteriovenous malformations, arterial stenosis/occlusion, and cerebral venous thrombosis: need dedicated vascular datasets and acquisition protocols.
- Hypoxic-ischemic injury and toxic/metabolic injury: need carefully defined populations, imaging time points, and reference labels.
- Congenital malformations and cortical dysplasia: need specialist annotations, population controls, and separate evaluation.
- Parkinsonian and other neurodegenerative syndromes: need disease-specific clinical cohorts; do not extrapolate ADNI results.

Migraine, psychiatric conditions, raised intracranial pressure, and many neurological disorders cannot be treated as generic labels recoverable from an arbitrary brain image. A model must have a defensible input-to-target relationship before it enters development.

## 6. Dataset acquisition and governance

For each candidate dataset, complete a record containing:

- Name, exact release, original URL, download date, checksums and citation.
- Access requirements, applicable terms, permitted uses and redistribution limits.
- Modality, sequences, file formats, scanner/site information and population.
- Patient, examination, series, slice and time-point identifiers where available.
- Label type: study, slice, point, bounding box, segmentation, event, or clinical endpoint.
- Class balance, negative cases, ambiguous labels, excluded cases and known limitations.
- Official splits and whether test labels are available.
- Relationships to other datasets that may reuse the same patients or images.

Do not assume a publicly described dataset is an unrestricted download. Some require registration, access approval, or acceptance of research-use terms. Public challenge test labels may remain hidden.

Important initial audits:

1. BRISC is a 2D image dataset with incomplete patient identification. Its paper reports that complete subject independence cannot be guaranteed. Its non-tumorous class is not equivalent to healthy [2].
2. BraTS releases and source collections may overlap. Deduplicate at patient level where mappings exist [1].
3. ISLES 2022 publishes 250 training cases; its 150 test cases are reserved for challenge evaluation. Create internal validation splits from training data without calling them the official test set [5].
4. ATLAS releases overlap. Preserve historical membership when constructing development and external evaluation partitions [6].
5. CHB-MIT is a pediatric, selected epilepsy cohort; performance is not evidence of adult population screening [14].
6. CQ500 is best treated as a held-out benchmark when possible. If used for training, it cannot simultaneously remain an independent test set [15].

Never label an unannotated condition as absent. A tumor dataset generally does not establish reliable negative labels for every other neurological disease.

## 7. Data organization and partitions

Use separate dataset adapters with a common internal schema. Preserve original files and write transformations to derived directories.

Suggested manifest fields:

```text
dataset_id, dataset_version, subject_id, study_id, series_id,
visit_id, modality, sequence, image_path, annotation_path,
annotation_type, target, site_id, age_group, split,
spacing, orientation, checksum, provenance, license_reference
```

Split by patient before slice extraction or augmentation. Keep all visits from one patient in the same partition unless the experiment explicitly uses a different leakage-controlled design. Freeze a test partition before tuning. Prefer institution-held-out evaluation when feasible.

For datasets without trustworthy patient identifiers, document the limitation and perform duplicate and near-duplicate checks; these checks cannot prove patient independence. Maintain an independent external evaluation cohort for strong generalization claims.

## 8. System architecture

```mermaid
flowchart TD
    A[De-identified study or EEG upload] --> B[Input validation and modality checks]
    B --> C[Dataset-specific preprocessing]
    C --> D[Capability router]
    D --> E[MRI tumor specialists]
    D --> F[MRI stroke and white matter specialists]
    D --> G[CT hemorrhage and structural specialists]
    D --> H[Angiography specialist]
    D --> I[EEG seizure specialist]
    E --> J[Structured findings and uncertainty]
    F --> J
    G --> J
    H --> J
    I --> J
    J --> K[Case-level evidence aggregation]
    K --> L[Viewer and human review]
    L --> M[Structured research report]
    M --> N[Optional cited literature assistant]
```

The router selects models using verified modality/sequence metadata and input checks. It does not send every scan to every model. Where multiple compatible targets are assessed, outputs are multi-label; abnormalities can coexist.

Use an API service for requests and a separate worker for inference. Begin with a simple job queue, one GPU worker and local artifact storage. Add distributed services only when load or isolation requirements justify them.

## 9. Input and preprocessing contracts

### MRI

- Read volumes with physical spacing and orientation preserved.
- Verify expected sequences rather than trusting filenames alone.
- Register same-examination sequences when necessary and inspect alignment.
- Apply training-consistent normalization and resampling.
- Preserve transformations so predictions can be mapped back to source space.
- Track skull stripping and other prerequisites used by the training dataset.
- Detect missing, corrupt, or unsupported inputs and abstain when requirements are unmet.

### CT and angiography

- Assemble series using reliable spatial metadata.
- Preserve and validate intensity rescaling and physical geometry.
- Apply task-specific windows and preprocessing.
- Distinguish non-contrast CT from CTA and other unsupported acquisitions.
- Do not apply MRI preprocessing to CT.

### EEG

- Validate channel names, montage, sample rate and recording duration.
- Apply documented filtering/resampling and artifact handling.
- Keep patient partitions fixed before creating overlapping windows.
- Retain timing so event predictions map to the original recording.

### 2D images

Provide an isolated BRISC research path. A JPEG without trustworthy physical geometry cannot support milliliter volume measurements, and unrelated slices must not be assembled into a fictional 3D scan.

## 10. Model portfolio

| Role | Baseline proposal | Advanced experiment | Activation condition |
|---|---|---|---|
| 3D lesion segmentation | 3D U-Net or nnU-Net-style baseline | Separate MRI encoders with feature fusion; compare a transformer-based model | Verified masks, geometry and patient-level evaluation |
| 2D tumor classification | Transfer-learned CNN | CNN/transformer ensemble | Reliable image labels and disclosed split limitations |
| CT hemorrhage | Slice encoder with study-level aggregation | 3D or attention-based aggregation | Correct mapping between slice and study targets |
| Aneurysm localization | Candidate detector with false-positive reduction | Joint vessel/context features where data supports them | Appropriate point/region supervision and location evaluation |
| White matter and small lesions | Task-specific 3D segmentation | Multiscale lesion refinement | Lesion-level sensitivity and false-positive evaluation |
| Longitudinal MS lesions | Aligned paired-scan baseline | Siamese temporal model | Same-patient paired scans and new-lesion labels |
| EEG seizures | 1D CNN or temporal convolutional network | Temporal attention/transformer | Event annotations, patient-independent testing |
| Atrophy measurements | Validated anatomical segmentation baseline | Longitudinal measurement model | Appropriate reference annotations and normative context |
| Research endpoint fusion | Simple tabular baseline | Matched MRI/PET/clinical feature fusion | Same-patient endpoints, aligned visits, no label leakage |

These are candidate architectures, not promised winners. Build and measure one baseline per task before adding complexity. A model registry can contain many specialists without loading them all into GPU memory at once.

## 11. Fusion design

### A. Early fusion

Stack aligned sequences from the same examination as channels. This is the first multimodal baseline, because it is comparatively simple and exposes whether multiple sequences add value.

### B. Feature fusion

Use sequence-specific encoders and combine learned features with concatenation, gating, or cross-attention. Candidate examples:

- DWI + ADC + FLAIR for ISLES lesion segmentation.
- T1 + contrast-enhanced T1 + T2 + FLAIR for a compatible BraTS task.

All inputs must correspond to the same patient and relevant examination, with spatial alignment verified. Compare against early fusion using the same partitions and training budget.

### C. Model ensembles

Combine predictions from models trained for the same target on compatible inputs. Calibrate and select combination weights on validation data. Quantify whether improvement justifies extra inference cost. Model disagreement is a useful signal, not a guarantee that errors are detected.

### D. Longitudinal fusion

Compare matched visits after registration. Display dates, acquisition changes, mask uncertainty and measurement variability. An apparent volume difference is not automatically biological progression.

### E. Cross-specialist evidence aggregation

Combine structured findings into a report without averaging unrelated disease probabilities. Do not normalize tumor, stroke and seizure scores into a single probability distribution or universal danger score.

Learned case-level fusion is a later experiment requiring a suitably labeled multimodal cohort. Do not create artificial pairs from unrelated MRI, CT, PET, or EEG subjects.

### F. Missing inputs

The default is to mark unsupported tasks as not assessed. Train missing-sequence variants only when their performance is separately evaluated. Do not silently synthesize a missing sequence and present it as acquired evidence.

## 12. Findings and uncertainty contract

Each result should carry:

```json
{
  "study_id": "research-study-001",
  "module_id": "stroke_mri",
  "model_version": "candidate-001",
  "assessment_status": "completed",
  "target": "ischemic_lesion",
  "finding_status": "candidate_present",
  "score": null,
  "calibration_version": null,
  "mask_artifact": "artifact-reference",
  "measurements": [],
  "input_series": ["dwi-series", "adc-series", "flair-series"],
  "limitations": [],
  "review_status": "unreviewed"
}
```

Allowed assessment statuses include completed, not_assessed, failed and abstained. Finding status applies only to completed tasks and must be interpreted within their scope.

Do not show an uncalibrated neural-network score as a patient's probability of disease. Choose thresholds on validation data, freeze them, and report sensitivity/false-positive trade-offs. Display unreliable or unfamiliar inputs for review; out-of-distribution detection cannot guarantee recognition of every unseen abnormality.

## 13. Viewer and human review workflow

The interface should provide:

1. Study import with de-identification checks and an input summary.
2. A list of compatible, unavailable and unsupported analyses.
3. Job progress and readable failure messages.
4. Axial, sagittal and coronal views for valid volumes.
5. Adjustable mask overlays and optional 3D lesion rendering.
6. Predicted lesion measurements with units and geometry provenance.
7. Confidence/disagreement layers with explanations of their limitations.
8. Manual mask editing and reviewer comments.
9. Side-by-side matched examinations when available.
10. Structured report preview and export.

Preserve the original model output when a reviewer edits a mask. Store the revision, reviewer, timestamp and model version. Corrections enter a reviewed annotation queue; they do not automatically become training truth or update deployed models.

The interface must not display an overall green 'brain healthy' badge. Show condition-specific results and explicit coverage gaps.

## 14. Reporting and RAG integration

Start with deterministic report templates populated from validated structured outputs. Include:

- Input examination and supported sequences.
- Model versions and processing status.
- Candidate findings, masks and measurements.
- Not-assessed tasks, quality problems and uncertainty.
- Reviewer edits and review status.
- Research-use statement and traceable artifact references.

Later, adapt TechRAG Architect's retrieval, reranking and citation-validation components for a curated neurological literature library. The RAG assistant may explain terms, locate methodology papers, and summarize documented limitations.

It must not invent imaging findings, convert missing evidence into negative results, give treatment instructions, or describe a source citation as validation of an individual prediction. A citation-format check is not a clinical factuality check. Evaluate report faithfulness against structured outputs and expert-reviewed references.

Keep literature indexing separate from patient information. Do not send identifiable data to external model providers by default.

## 15. Backend, storage and interfaces

Suggested components:

- Python and PyTorch/MONAI for imaging pipelines [16].
- A separate EEG processing adapter and temporal model pipeline.
- FastAPI for study registration, inference jobs, findings and review actions.
- A task queue and worker processes for long-running processing.
- PostgreSQL for metadata, job states, model records and review history.
- Filesystem or object storage for original scans, derived images, masks and reports.
- A web interface with a medical-image viewer selected after a DICOM/NIfTI compatibility prototype.
- TensorBoard or an experiment tracker for training and evaluation.

Proposed API surface, not implemented endpoints:

```text
POST /studies                 Register an uploaded research study
GET  /studies/{id}            Read metadata and available series
GET  /studies/{id}/capabilities
POST /jobs                   Request compatible analyses
GET  /jobs/{id}               Read processing state
GET  /studies/{id}/findings    Read structured findings
POST /findings/{id}/reviews   Save review and annotation revisions
POST /studies/{id}/reports    Generate a research report
GET  /models                 Read model capability cards
GET  /evaluations             Inspect recorded benchmark results
```

Support cancellation, explicit failures, resource limits, and idempotent job submission. The health endpoint should distinguish API availability from model and worker readiness.

## 16. Repository structure

```text
neurofusion/
  backend/
  frontend/
  pipelines/
    preprocessing/
    registration/
    mri/
    ct/
    angiography/
    eeg/
  models/
    tumor/
    stroke/
    hemorrhage/
    vascular/
    white_matter/
    neurodegeneration/
    seizures/
    fusion/
  datasets/
    adapters/
    manifests/
    splits/
  evaluation/
    metrics/
    benchmarks/
    calibration/
    external_validation/
  reporting/
    templates/
    rag/
  configs/
  scripts/
  tests/
  docs/
  artifacts/                 Ignored or stored outside Git
  README.md
```

Large scans, protected data and model artifacts should not be committed to the source repository. Track reproducible manifests, configuration and permitted references instead.

## 17. Training workflow

1. Audit one dataset and visually inspect representative labels.
2. Freeze patient-level development, validation and test partitions.
3. Implement a deterministic adapter and geometry checks.
4. Run a tiny-sample overfit experiment to debug the training pipeline.
5. Train a simple baseline with recorded seeds and configuration.
6. Evaluate errors by lesion size, site, sequence and population where metadata supports it.
7. Introduce fusion or another architecture as a controlled experiment.
8. Calibrate outputs and select operating thresholds using validation data only.
9. Freeze the candidate and evaluate on the untouched test partition.
10. Evaluate on an external compatible cohort before broader claims.

Record preprocessing version, dataset checksums, split manifest, seed, model settings, training budget, checkpoint selection rule and environment dependencies. Save failed experiments as well as successful ones.

For multi-task training with incomplete labels, use explicit label masks so an unknown label contributes no false negative supervision. Monitor each task separately for negative transfer.

## 18. Evaluation plan

| Task | Required measurements |
|---|---|
| Study/image classification | Sensitivity, specificity, precision, AUROC/AUPRC where appropriate, confusion matrix, calibration |
| Segmentation | Dice, boundary distance such as HD95, volume error, lesion-level sensitivity and false positives |
| Small-lesion localization | Lesion sensitivity at stated false-positive rates, stratified by lesion size |
| EEG events | Event sensitivity, false alarms per hour, detection latency with a documented event-matching rule |
| Longitudinal measurement | Agreement with reference changes, registration failures and measurement repeatability |
| Reports | Correctness of measurements, unsupported claims, omitted limitations and citation relevance |
| System | Runtime, peak memory, job failures, missing-input handling and reproducibility |

Calculate confidence intervals at the patient level where appropriate; slices from one patient are correlated. Define empty-mask handling and do not silently omit normal or failed cases.

The core fusion study should compare a single sequence, channel stacking, and separate-encoder fusion using identical partitions. Repeat runs when feasible and report both performance and computational cost. A modest result with honest external testing is stronger than an inflated slice-level accuracy.

Do not choose a generic 95% accuracy target. Set research acceptance thresholds with a clinical collaborator for the specific task and intended use, including acceptable false positives and subgroup failures. Public benchmark success is not clinical deployment approval.

## 19. Testing and reliability

Meaningful automated checks should cover:

- Volume orientation, spacing, and mask alignment round trips.
- Correct patient split membership and duplicate detection.
- Sequence availability and routing to compatible models.
- Preservation of unknown labels during training.
- Measurement units and transformation back to source space.
- Job cancellation, failure handling and artifact persistence.
- Review history and preservation of original model outputs.
- Report values matching structured findings.
- Refusal to infer unsupported capabilities or fabricate missing data.

Use de-identified fixtures. Include a small end-to-end research case for each activated module, plus corrupt and incomplete inputs. Test resource failures without damaging stored studies.

## 20. Hardware and resource planning

Do not buy hardware before benchmarking the first pipeline. Memory demand depends on patch size, sequence count, network width, batch size and precision.

As an initial planning assumption, a single modern GPU can support small 2D and patch-based 3D experiments; full-volume transformers and multiple simultaneous models may require substantially more memory. Use smaller patches, mixed precision where numerically appropriate, gradient accumulation, and sliding-window inference when necessary.

Collect these measurements before estimating project cost:

- Downloaded and expanded dataset sizes.
- Preprocessing disk footprint and duration.
- GPU memory for one forward/backward pass.
- Steps per second and validation duration.
- Inference latency for a complete study.
- Storage for checkpoints, derived volumes and reports.

Run one specialist at a time initially. Schedule experiments rather than leaving every model resident in memory. Cloud use requires a cost estimate and confirmation that data terms and privacy arrangements permit it.

## 21. Development releases and gates

| Release | Deliverables | Exit gate |
|---|---|---|
| 0: Feasibility | Dataset register, resource benchmark, selected first task, frozen splits | Access, labels and compute are adequate |
| 1: MRI baseline | ISLES or BraTS baseline, geometry pipeline, evaluation | Reproducible results and inspected failure cases |
| 2: Fusion research | Early versus feature fusion, missing-input behavior | Controlled comparison with documented outcome |
| 3: Usable research app | Import, viewer, measurements, jobs, reports | End-to-end held-out case and failure-path checks |
| 4: Second specialist | Tumor or stroke branch not selected first, then CT hemorrhage | Independent task evaluation and routing tests |
| 5: Broader imaging | Aneurysms, WMH, microbleeds/lacunes, selected tumor extensions | Per-module data and validation gates |
| 6: Temporal and EEG | Longitudinal analysis, MS lesions, EEG events | Suitable paired/event data and separate evaluation |
| 7: Multimodal research | ADNI-based endpoints, matched-data fusion | Endpoint definition and leakage-controlled cohort |
| 8: Review and knowledge | Reviewer workflows and cited literature assistant | Faithful reports and traceable human changes |

Viewer, reporting and review work may progress alongside model work. Advanced modules remain disabled until their own gates pass. This broad scope is a multi-release research program, not a short assignment; timing should follow the feasibility benchmark and available team effort.

## 22. Progress dashboard

Maintain a project board with a row per module and these columns:

```text
Dataset access | Label audit | Split freeze | Baseline |
Fusion experiment | Internal evaluation | External evaluation |
Viewer integration | Documentation | Activation status
```

Show training/validation curves, task metrics, confidence intervals, throughput, GPU memory and representative failure cases. Keep performance grouped by dataset and target; do not publish one blended accuracy for the whole platform.

Every release should include before/after model comparisons on the same held-out cases. Record whether added complexity improved results. Retaining a simpler baseline is a valid outcome.

## 23. Privacy and clinical boundaries

Use research datasets and de-identified examples for development. Check both metadata and burned-in image identifiers before sharing. Limit access, preserve review/audit history and define retention/deletion procedures.

The prototype must not make treatment recommendations, declare all disease absent, generate an unsupported urgency score, or operate as autonomous emergency triage. Clinical deployment would require appropriately designed clinical validation and review of the applicable institutional and regulatory requirements with qualified professionals.

No model can establish full coverage of all brain harm from arbitrary inputs. The application must say which findings were assessed, which were not, and why.

## 24. First implementation checklist and deliverables

Immediate steps:

1. Confirm CPU, GPU/VRAM, RAM, available disk, operating system, team size and project deadline.
2. Choose ISLES fusion as the default first experiment, or explicitly choose BraTS.
3. Request/download the chosen training data through its official channel and record terms.
4. Inspect a small number of complete studies and masks in a viewer.
5. Build the manifest and patient-level partitions.
6. Implement one baseline with a tiny debugging run before full training.
7. Add evaluation, artifact provenance and a minimal viewer.
8. Compare fusion methods; then decide which specialist to add next.

Final research deliverables:

- Reproducible repository and setup documentation.
- Dataset provenance register and fixed partition manifests.
- Model cards and per-module capability registry.
- Baselines, fusion comparisons and saved model artifacts.
- Internal and external evaluation reports with limitations.
- Interactive scan/EEG review application.
- Structured report export and optional cited literature assistant.
- Recorded demonstration using de-identified held-out examples.
- Known-failures register and a prioritized extension roadmap.
- The six high-priority feature deliverables and the advanced federated-learning experiment specified in Section 26.

Completion of this manual is a planning deliverable only. Dataset downloads, trained weights, application code, and clinical validation are not included in this deliverable.

## 25. Primary sources and dataset starting points

Sources checked on 5 October 2026. A linked dataset or challenge is a starting point, not confirmation that every file or annotation is currently downloadable without approval.

1. **BraTS 2021:** MRI sequences, labels, preprocessing, access and overlap with previous releases. https://www.med.upenn.edu/cbica/brats2021/
2. **BRISC paper and dataset:** 2D classification/segmentation, source overlap and patient-identity limitations. https://www.nature.com/articles/s41597-026-06753-y and https://www.kaggle.com/datasets/briscdataset/brisc2025/
3. **BraTS-METS research description:** brain metastasis segmentation. https://arxiv.org/abs/2306.00838
4. **BraTS-PEDs collection:** pediatric tumor imaging. https://www.cancerimagingarchive.net/collection/brats-peds/
5. **ISLES 2022:** DWI/ADC/FLAIR stroke-lesion dataset, public training and hidden testing. https://www.nature.com/articles/s41597-022-01875-5 and https://doi.org/10.5281/zenodo.7153326
6. **ATLAS:** current dataset description and release notes. https://fcon_1000.projects.nitrc.org/indi/retro/atlas.html and https://github.com/npnl/ATLAS
7. **RSNA intracranial hemorrhage:** task and dataset provenance. https://www.rsna.org/artificial-intelligence/ai-image-challenge/RSNA-Intracranial-Hemorrhage-Detection-Challenge-2019 and https://pubs.rsna.org/doi/10.1148/ryai.2020190211
8. **RSNA aneurysm challenge:** modality and localization scope. https://www.rsna.org/artificial-intelligence/ai-image-challenge/intracranial-aneurysm-detection-ai-challenge
9. **WMH challenge publication:** T1/FLAIR images and segmentation labels. https://pmc.ncbi.nlm.nih.gov/articles/PMC7590957/
10. **VALDO challenge and training data:** microbleeds, lacunes and enlarged perivascular spaces. https://valdo.grand-challenge.org/ and https://zenodo.org/records/4520773
11. **MSSEG-2:** listed by MICCAI as the multiple-sclerosis new-lesion segmentation challenge. Dataset contents/access require confirmation; the linked record could not be opened during preparation. https://www.miccai2021.org/en/MICCAI2021-CHALLENGES.html and https://doi.org/10.5281/zenodo.4575408
12. **ADNI:** MRI, PET and documentation of the longitudinal research cohort. https://adni.loni.usc.edu/data-samples/adni-data/neuroimaging/mri/ and https://adni.loni.usc.edu/data-samples/adni-data/neuroimaging/pet/ and https://adni.loni.usc.edu/help-faqs/adni-documentation/
13. **TUH EEG:** seizure corpus and access information. https://isip.piconepress.com/projects/tuh_eeg/ and https://isip.piconepress.com/projects/nedc/html/tuh_eeg/index.shtml
14. **CHB-MIT:** pediatric scalp EEG seizure recordings. https://physionet.org/content/chbmit/1.0.0/
15. **CQ500 source study:** CT hemorrhage, fracture, mass effect and midline shift labels. Verify present download access separately. https://arxiv.org/abs/1803.05854
16. **MONAI:** medical-imaging framework and examples. https://github.com/Project-MONAI/MONAI and https://github.com/Project-MONAI/tutorials
17. **MONAI Label:** annotation workflows and active-learning interfaces. https://docs.monai.io/projects/label/en/latest/index.html and https://github.com/Project-MONAI/MONAILabel/wiki/Active-Learning
18. **MONAI federated learning:** interfaces for federated model development. https://monai.readthedocs.io/en/latest/fl.html

## 26. Approved priority feature expansion

All seven features below belong to the planned project. High priority means they should be integrated into the core research workflow; advanced means the feature depends on mature baselines and requires a later experimental release. Adding these requirements does not imply that their implementation or validation has begun.

### 26.1 Active-learning queue — high priority

Purpose: prioritize useful unlabeled development cases for qualified annotation, using a combination of uncertainty and diversity instead of annotating only easy or repetitive cases.

Workflow:

1. Score eligible development cases using a versioned selection strategy.
2. Present ranked cases with selection reasons and task compatibility.
3. Assign annotation tasks to reviewers.
4. Route corrected labels through review and, where needed, adjudication.
5. Freeze an approved annotation version for a new training experiment.

Never sample from protected test cohorts for training. Do not automatically retrain or replace a running model after a correction. Candidate selection is annotation prioritization, not clinical urgency prioritization. MONAI Label is a candidate implementation foundation [17].

Acceptance: compare active selection against random selection under equal annotation budgets; report held-out performance, annotation effort and selection diversity. Verify test-set exclusion and trace each new training label to its approved revision.

### 26.2 Finding-to-evidence links — high priority

Purpose: let a reviewer trace every finding and measurement to its actual source evidence.

Each finding stores the study and series identifiers, physical-space coordinates, frame/slice or EEG interval, original and derived artifact versions, model version, preprocessing version, and mask revision. Volume measurements link to both the mask and spacing used in their calculation.

Clicking a report finding opens the corresponding viewer location and overlay. Preserve the coordinate transforms rather than relying on a slice index that may change after resampling. Exported reports retain stable evidence identifiers; access-controlled links must not expose private files publicly.

Acceptance: select a finding after resampling and verify that the viewer opens the correct source location; verify report links still resolve after a new model run; verify unauthorized access is denied and missing artifacts produce explicit errors.

### 26.3 Collaborative review and adjudication — high priority

Purpose: collect independent assessments and resolve disagreements without overwriting evidence.

Provide assignment, independent reviewer submissions, a disagreement comparison view, adjudication, and an approved annotation state. Reviewer submissions can be hidden from each other until both are complete. Preserve each original assessment and the adjudicator's rationale.

Use explicit states: assigned, in_review, submitted, disputed, adjudicated, approved. Prevent accidental overwrites through revision checks. Link any annotation used for training to its approved state and provenance.

Acceptance: two reviewers can submit different masks independently; discrepancies are displayed; adjudication creates a new version while preserving both inputs; only approved versions enter the training export. Measure inter-reviewer agreement without treating agreement alone as proof of correctness.

### 26.4 Dataset leakage detector — high priority

Purpose: identify evidence that training, validation and test partitions are not independent.

Checks include exact file hashes, normalized image hashes, near-duplicate candidates, shared patient identifiers, repeated visits, and documented cross-dataset patient mappings. Account for dataset re-releases and shared source collections. Near-duplicate similarity should generate review candidates rather than automatically deleting potentially distinct medical images.

Output a leakage report with suspected pairs/groups, detection method, affected partitions and resolution status. Confirmed cross-partition patient overlap or duplicate leakage blocks a new training run until partitions are repaired and versioned. Record unresolved patient-identity limitations prominently.

Acceptance: seeded duplicate and patient-overlap fixtures are detected; known clean fixtures pass; the pipeline blocks confirmed leakage; the split repair is reproducible. Passing these checks cannot prove independence when patient metadata is unavailable.

### 26.5 Fusion experiment lab — high priority

Purpose: make the value of fusion measurable and inspectable through the website.

Support controlled comparisons of single-sequence, channel-stacking, separate-encoder feature fusion, and optional same-task ensembles. Record the exact inputs, split, preprocessing, seeds, training budget, checkpoint rule, calibration procedure and inference cost for every run.

Display per-task metrics, patient-level uncertainty intervals where feasible, paired case comparisons, and performance by lesion size/site where metadata allows. Include missing-sequence experiments only for model configurations designed to accept those inputs; otherwise record an abstention.

Acceptance: launch a reproducible comparison on frozen development partitions, select configurations using validation data, and run the final frozen comparison on untouched test data. Report cases where fusion fails to improve the baseline as well as successes. Do not tune on test results.

### 26.6 Robustness testing lab — high priority

Purpose: measure how performance and abstention behavior change under defined input variation.

Create versioned test suites for missing sequences, supported resolution changes, plausible intensity/noise perturbations, registration offsets, corrupted metadata, and complete processing failures. Separate plausible acquisition variation from deliberately invalid inputs. Keep image geometry and reference labels consistent when applying spatial transforms.

Show degradation curves, false positives, sensitivity, runtime and rejection/abstention rates. Synthetic perturbations supplement external-site evaluation; they do not establish real-world robustness. Extreme artificial image manipulations must not be presented as realistic clinical examples.

Acceptance: reproduce the same perturbations from a fixed configuration; verify transformed label alignment; reject unsupported input combinations explicitly; generate a clean-versus-perturbed comparison and a failure report. Set operating gates with the task's research acceptance criteria rather than inventing a universal robustness score.

### 26.7 Federated-learning experiment — advanced priority

Purpose: study training across separate research clients while keeping their raw data local to each client. Start with a simulation on permitted research data; this is not a hospital integration commitment.

Prerequisites: a reproducible centralized baseline, local-only baselines, compatible target definitions and preprocessing, patient-independent client partitions, and an untouched evaluation cohort. Prefer real site partitions when available; label artificial partitions as simulated sites.

Proposed components:

- A coordinator that versions global checkpoints and training rounds.
- Client workers that run approved local training configurations.
- A simple aggregation baseline such as FedAvg, followed by more complex strategies only if needed.
- Per-client and aggregate metrics, communication accounting and client-failure handling.
- Versioned round checkpoints and reproducible client participation records.

Use MONAI's federated-learning interfaces where appropriate [18]. Compare federated, local-only and centralized experiments under documented and reasonably comparable training budgets. Report unequal client data distributions and performance at each client instead of relying solely on a pooled score.

Keeping raw data local does not guarantee privacy: model updates and metadata can leak information. Before real institutional use, establish a threat model and evaluate authentication, transport protection, update validation, secure aggregation and any differential-privacy mechanism appropriate to the design. Do not claim these protections are implemented or effective without evidence.

Acceptance: complete reproducible simulated multi-client rounds; compare all three baselines; verify raw scans are not transferred by the application protocol; test interrupted clients and checkpoint recovery; document remaining privacy and generalization limitations.

### 26.8 Integration into the release plan

| Feature | Start point | Required dependencies | Completion evidence |
|---|---|---|---|
| Leakage detector | Release 0 | Dataset manifests and identifiers | Audited partitions and blocking checks |
| Fusion lab | Release 2 | Reproducible single-task baseline | Controlled comparison report |
| Robustness lab | Releases 2–3 | Frozen evaluation pipeline and geometry tests | Degradation and abstention report |
| Evidence links | Release 3 | Artifact identifiers and coordinate transforms | Viewer/report traceability checks |
| Collaborative review | Release 3 onward | Accounts, permissions and immutable annotations | Independent review and adjudication workflow |
| Active learning | After review and baseline evaluation | Approved annotation export and protected test cohorts | Equal-budget selection experiment |
| Federated learning | After the centralized baseline and audit tooling | Compatible client datasets and reproducible training | Simulated multi-client benchmark and limitations report |

These additions supplement the existing releases rather than requiring every disease model to be finished first. Active learning and federation should initially target one well-tested specialist.

### 26.9 Repository additions

Extend the Section 16 structure with:

```text
datasets/leakage/             # Hashing, overlap checks and audit reports
annotation/active_learning/  # Candidate scoring and selection strategies
annotation/review/           # Review states and approved-label exports
provenance/                  # Findings, artifact versions and coordinates
evaluation/fusion/           # Controlled fusion comparisons
evaluation/robustness/       # Perturbation suites and degradation analysis
federated/coordinator/       # Round scheduling and aggregation
federated/client/            # Local training and update exchange
configs/federated/           # Versioned client and experiment settings
frontend/research/           # Review queues, evidence and experiment views
tests/research_workflows/    # Leakage, review, provenance and federation checks
```

This is a logical directory proposal; adapt frontend routes to the framework selected during implementation. Add API contracts for annotation assignment/submission, adjudication, active-learning selection, evidence lookup and experiment submission. Keep federated coordinator controls separate from public inference endpoints.

### 26.10 Expansion deliverables

- A dataset leakage audit and frozen partition record.
- A working finding-to-evidence navigation workflow.
- Independent review, disagreement comparison and adjudication.
- A reviewed active-learning annotation cycle with an equal-budget baseline.
- A fusion comparison dashboard and reproducible experiment configurations.
- A robustness test suite with documented limitations.
- A federated-learning simulation benchmark and threat-model summary.

Status of every feature in this expansion: planned, not implemented.
