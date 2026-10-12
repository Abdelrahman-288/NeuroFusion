> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# Implementation status

2026-10-09 full-volume review workbench implemented: all 20 cases, every slice in three planes, annotation toggle, source hashes, persistent review revisions and stale-edit rejection. Real-cohort HTTP checks cover 120 boundary slices; no expert review submissions were generated. Added tested development-only annotation selection component; full active-learning benchmark remains pending. Full release dashboard tracks 24 unequal requirement groups; no measured overall percentage. UCSF qualification remains 2/10 and expert reviews 0/20. See `COHORT_REVIEW_WORKBENCH.md`, `ACTIVE_LEARNING.md`, and `release_status.json`.

2026-10-09 exposure-audit preparation: 4/4 engineering deliverables complete; 20/20 patient records audited across 1,795 UTF-8 text files. Nine matching files are inventory/intake references; zero unclassified references. One encoding-skipped glossary separately decoded and checked. Independence remains unverified; expert reviews 0/20; UCSF qualification remains 2/10. See `UCSF_EXPOSURE_REVIEW.md`.

2026-10-09 acquisition stage complete: 20/20 new UCSF MRI/annotation pairs (40 files) acquired and audited. SHA256, native geometry, numeric labels, known patient/BraTS mapping exclusions and exact canonical voxel duplicates checked. UCSF research qualification advances to 2/10 gates; overall project percentage remains unmeasured. No training or inference on these cases. Next: cohort independence/exposure audit and expert review preparation. See `UCSF_ACQUISITION.md` and `progress_tracker.json`. Earlier entries are historical snapshots.

2026-10-08 qualification planning stage: 4/4 deliverables complete. UCSF research qualification gates: 1/10 passed; this is not full-project completion. Provisional acquisition queue: 20 new patients selected from 192 metadata candidates; 0 pairs acquired, independence unverified, cohort unfrozen. Next: acquisition and integrity audit, no model inference. See `QUALIFICATION_ROADMAP.md` and `progress_tracker.json`. Historical percentages below are superseded.

2026-10-08 clipping from initialization stage complete: 3 training runs, 15 checkpoints and 12 reproduced native predictions. Decision: confirmation failed; retain baseline. 203 tests passed. Current stage 4/4 (100%) complete. Historical overall 86% is an informal estimate, superseded by explicit stage tracking in `progress_tracker.json`; it is not measured project completion. See `UCSF_CLIPPING_CONFIRMATION.md`.

2026-10-08 clipping diagnostic intervention complete. Strict first attempt aborted at update 244; separately recorded AMP-compatible variant completed. Native train-subset Dice 0.7126, validation 0.4996; excess false positives and near-zero-overlap case remain. 203 tests passed; no promotion. Overall estimate stays ~86%. See `UCSF_GRADIENT_CLIP_PROBE.md`.

2026-10-08 exact epoch replay complete: 310 optimizer updates reproduced with identical final model/optimizer/RNG states. Fixed probe outputs become persistently empty after step 157; step 156 had the largest finite gradient/update. Cause not yet proven; no fix or promotion. 201 tests passed. Overall estimate remains ~86%. See `UCSF_EPOCH_REPLAY.md`.

2026-10-08 training diagnostics completed: 80 case/checkpoint evaluations; seed-43 empty predictions also occur on four fixed training cases. Lower-rate excess false positives also occur on training examples. 200 tests passed; no model or threshold changes. Overall estimate remains ~86%. See `UCSF_TRAINING_DIAGNOSTICS.md`.

2026-10-08 paired-seed confirmation complete: seeds 42/43/44 compared with four additional five-epoch runs. Decision: confirmation failed; retain baseline. 198 tests passed; new checkpoints reproduced 16 saved masks. No promotion. Overall rough estimate remains ~86%. See `UCSF_LR_CONFIRMATION.md`.

2026-10-08 lower-learning-rate screen completed: final native development Dice 0.5089 vs baseline 0.4267; all four predefined checks passed. Candidate awaits paired-seed confirmation; zero-overlap patient remains unresolved; no promotion. 196 tests passed. Overall rough estimate ~86%. See `UCSF_LOW_LR.md`.

2026-10-08 balanced-sampling experiment complete: five epochs, final native development Dice 0.3082 vs baseline 0.4267; three of four predefined checks failed. Candidate rejected, baseline retained, no promotion. 196 tests passed. Overall estimate remains ~85%. See `UCSF_BALANCED_SAMPLING.md`.

2026-10-08 UCSF error review completed: 48 three-plane views, component sizes and missed/extra predictions audited; reports linked in viewer. Six of ten annotation components have no overlap (four are 1-7 voxels); eleven of eighteen predicted components have no overlap. Balanced sampling experiment specified but not run. Overall rough estimate remains ~85%; model performance unchanged. See `UCSF_SPECIALIST_ERRORS.md`.

2026-10-08 UCSF specialist baseline: five epochs completed; final original-grid development Dice 0.4267 across four patients, including one zero-overlap case. Five checkpoints saved; reload reproduced masks/metrics. 192 tests passed. No promotion. Current rough implementation estimate ~85%. See `UCSF_SPECIALIST_BASELINE.md`. Entries below are historical snapshots.

2026-10-08 UCSF loader/GPU readiness: all 3,100 slices cached; two batch-8 RTX 4070 steps passed, no checkpoint saved. 190 tests passed. Current rough implementation estimate ~84%. See `UCSF_LOADER_GPU.md`.

2026-10-08 dedicated UCSF specialist plan: numeric foreground target defined; 16/4 patient-disjoint development roles recorded, 3,100 slices retained. Training not started. See `UCSF_SPECIALIST_PLAN.md`; overall estimate ~83%.

2026-10-08 viewer integration: five UCSF review reports connected to the local application with restricted artifact routes. 180 tests passed; five pages and 389 linked assets verified over HTTP. Review gates remain pending; estimate ~83%. See `UCSF_VIEWER_INTEGRATION.md`.

2026-10-08 native metrics: binary native-grid overlap/volume metrics added with explicit empty-case policies and geometry rejection. Synthetic validation only; UCSF remains unscored. See `NATIVE_METRICS.md`.

2026-10-08 cohort separation: 13/20 pilot patients have BraTS mappings; 192 conservative candidate patients remain after patient-level exclusions. Inventory only, not a verified test cohort. See `PDGM_COHORT_SEPARATION.md`.

2026-10-08 alignment gallery: 20 exams, 180 original-grid views, overlay toggle and 360 verified PNGs. Expert alignment reviews remain 0/20; overall estimate stays ~83%. See `PDGM_ALIGNMENT_GALLERY.md`.

Updated: 2026-10-08 (Africa/Cairo). This is the implementation record; the PDF
describes the larger planned platform and has not been rewritten by this code change.

2026-10-08 intake milestone: one real UCSF-PDGM T1c/mask pair imported as 155 slices; 19 pilot exams await files. One slice has a downsampling label-loss warning. No inference or external scoring. See `PDGM_FIRST_IMPORT.md`. Latest full regression: 152 passed after adding resolution QA (53.68 seconds); model code remains unchanged.

2026-10-08 resolution QA: real-case categorical roundtrip and 26-connected component-loss analysis completed at three sizes. Native reference-mask policy documented; label mapping remains pending. See `PDGM_RESOLUTION_AUDIT.md`.

2026-10-08 batch 002: two additional real MRI/mask pairs downloaded and imported; cumulative 3/20 exams, 465 slices, zero import failures. Latest regression remains 152 passed; this batch changes data and records only. See `PDGM_BATCH_002.md`.

2026-10-08 batch 003: four further real MRI/mask pairs acquired; cumulative 7/20 exams, 1,085 slices, zero import failures. Five exams have slice-level resizing warnings. Latest code regression remains 152 passed; this batch changes data and records only. See `PDGM_BATCH_003.md`.

2026-10-08 pilot acquisition complete: all 20 preselected pairs imported (3,100 slices), zero failures. Ten exams have resizing warnings affecting 19 slices. External evaluation remains pending. Latest code regression remains 152 passed; this stage changed data and documentation. See `PDGM_PILOT_COMPLETE.md`.

2026-10-08 full pilot resolution audit: 60 comparisons completed; 155 tests passed. Added checksum-validated cohort runner and technical review queue. Label meanings and anatomical alignment remain pending. See `PDGM_PILOT_RESOLUTION.md`.

2026-10-08 target contract: candidate numeric unions and strict validation implemented; native-mask inventory covers all 20 exams. Current binary BRISC output is not established as a compatible UCSF region target. See `PDGM_TARGET_CONTRACT.md`.

| Stage | Description | State |
|---|---|---|
| 1 | Scope and task contracts | Initial ISLES research task selected; broad coverage remains in guide |
| 2 | Repository and development workflow | Foundation implemented |
| 3 | GPU environment | Verified: isolated Python 3.11, PyTorch 2.5.1+cu121, RTX 4070 CUDA forward/backward passed |
| 4 | Dataset registry | ISLES v2.3.1 downloaded, checksums verified, attribution recorded |
| 5 | Data quality inspection | 250 studies inspected automatically; sample previews generated; full expert review pending |
| 6 | Patient partitions and leakage | Two subjects quarantined; 248 retained; 174/37/37 split frozen after descriptive distribution review; imbalance documented |
| 7 | Preprocessing | DWI orientation/normalization implemented; real-study mask roundtrip passed; registration/resampling pending |
| 8 | Tiny debugging baseline | Synthetic and fixed real-training-patch overfit checks passed; whole-study/generalization performance not established |
| 9 | Training engine | Full-cohort disk-backed loader, mixed precision and epoch checkpoints implemented; five epochs completed; exact resume verified on synthetic control |
| 10 | First specialist evaluation | Baseline lesion analysis complete; component-balanced sampler reached mean Dice 0.3607 and lesion recall 24.6%; external evaluation pending |
| 11 | Experiment dashboard | Full-cohort HTML curves, per-case results, model card and prediction comparisons implemented; web dashboard pending |
| 12 | Fusion lab | First full DWI/ADC experiment and lesion comparison complete; Dice 0.3103 below DWI baseline; broader fusion still planned |
| 13 | Robustness and abstention | Classifier, tumor segmentation and DWI development stress tests implemented; segmentation extension covers 721 images and 37 volumes across six conditions with metric replay (see SEGMENTATION_ROBUSTNESS.md). Perturbation failures remain; calibrated reliable abstention is still partial (see UNCERTAINTY_DECISIONS.md). |
| 14 | Common prediction format | Version-1 result schema, pinned checkpoints and label-free inference implemented |
| 15 | Backend and storage | Loopback HTTP API, SQLite job records and local files implemented; authentication pending |
| 16 | Jobs and compatible model routing | Persistent bounded queue, single background worker, status/history and restart recovery implemented |
| 17 | Image viewer | PNG overlays, opacity and DWI slice navigation implemented |
| 18 | Findings and evidence links | Reviewer notes linked to displayed slices and result JSON hashes; automated findings pending |
| 19 | Reporting and grounded explanations | Offline HTML/JSON reports with provenance, previews and separate review entries; external grounded explanations pending |
| 20 | Integrated web release | Local upload prototype implemented; deployment pending |
| 21 | Collaborative review | Local append-only review entries and JSON export implemented; accounts and multi-user collaboration pending |
| 22 | Active learning | Planned |
| 23 | Retraining and model promotion | Planned |
| 24 | Tumor specialists | BRISC classifier and 2D segmenter trained; classification accuracy 82.82%, segmentation Dice 0.6699; external validation pending |
| 25 | CT specialists | Planned |
| 26 | Vascular/small-lesion specialists | Planned |
| 27 | Longitudinal analysis | Planned |
| 28 | EEG and cohort research | Planned |
| 29 | Federated simulation | Planned |
| 30 | Deployment and maintenance | Planned |

## Evidence to inspect

2026-10-07 update: 146 tests passed. Confidence temperature scaling worsened separate-group development metrics and was rejected; viewer unchanged. See `CALIBRATION_EXPERIMENT.md`. Tumor segmentation results are in `TUMOR_SEGMENTATION.md`; progress is in `PROJECT_PROGRESS.md`. Lesion analysis is in `LESION_ANALYSIS.md`; the controlled sampling comparison is in `COMPONENT_SAMPLING_EXPERIMENT.md`. Data findings are in `DATA_QC_FINDINGS.md`;
earlier debugging is in `BASELINE_RUN.md`; current full-cohort results and coverage
verification are in `COHORT_TRAINING.md` and the run's `MODEL_CARD.md`.

Verified on 2026-10-05: 16 tests passed; the 12-patient synthetic demo and its
independent saved-manifest audit passed; `pip check` found no broken requirements.
The GPU smoke test passed using the isolated project executable. This small test
does not predict full model training throughput or memory requirements.

- `experiments/environment.json`: actual device and forward/backward result.
- `experiments/foundation-tests.xml`: regression suite results.
- `experiments/foundation-demo/audit.json`: synthetic end-to-end audit.
- `experiments/environment-freeze.txt`: exact installed environment snapshot.

These paths are local ignored artifacts. Their existence and results, not this
checklist alone, establish completed verification. The first five-epoch full-cohort
run is complete; predictions remain uneven. No website is deployed.

## Next real-data gate

See `COHORT_TRAINING.md`. Full-cohort training and voxel/volume evaluation are
complete for the first baseline. Component-balanced sampling then reached mean Dice
0.3607 and matched 74/301 components, while increasing unmatched predictions.
First ADC fusion comparison is complete and underperformed DWI-only. BRISC
classification and segmentation baselines are now trained and evaluated. Next:
external MRI acquisition and a verified task-specific adapter/protocol. UCSF-PDGM metadata intake and synthetic volume checks are complete; one pilot MRI/mask pair is now imported; 19 remain, with label and alignment review pending. See `PDGM_INTAKE.md`. Source review and control-tested 2D overlap auditing are complete; see `EXTERNAL_DATA_READINESS.md`. See `CONTRAST_EXPERIMENT.md`. Further model work includes
false-positive reduction, multi-seed experiments and independent evaluation.
See `LESION_ANALYSIS.md` and `COMPONENT_SAMPLING_EXPERIMENT.md`. Holdout remains unused.

Target-contract validation: full regression **164 tests passed**, including nine new union, invalid-label, empty-region and evaluation-gate checks.

Cohort-separation regression: **169 tests passed** in 38.66 seconds, including five new patient identity and follow-up exclusion checks.

Native-metrics validation: full regression **179 tests passed** in 39.08 seconds, including 10 new metric/geometry cases.
