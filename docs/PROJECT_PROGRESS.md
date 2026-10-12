> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# NeuroFusion progress

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

Historical estimate (superseded): approximately 86%, not a measured completion percentage.
This is a rough scope estimate, not measured effort, clinical readiness or accuracy.
Target-contract update: primary-source BraTS mapping documented as a candidate for UCSF v5; native numeric-union inventory completed for 20 exams. Version confirmation and equivalence to the binary BRISC model remain unresolved. No scoring. See `PDGM_TARGET_CONTRACT.md`.
Resolution QA update: all 20 pilot exams audited at 128, 240 and 256 pixels. At 128, 14 exams lose overlap with 267 annotation components; 240/256 categorical roundtrips were exact for this pilot. Native masks remain scoring truth; model inputs unchanged. 155 tests passed. See `PDGM_PILOT_RESOLUTION.md`. Overall estimate remains ~83%.
Current intake update: all 20 pilot exams are prepared (3,100 slices); zero awaiting files or failures. Batch 004 acquired the final 13 pairs. Ten exams have slice-level resizing warnings affecting 19 slices. This completes pilot acquisition, not clinical/external validation or the full UCSF collection. See `PDGM_PILOT_COMPLETE.md`.
Confidence update: the temperature calibrator was rejected after worsening separate-group development metrics; viewer scores remain unchanged. See `CALIBRATION_EXPERIMENT.md`.
The batch importer and 3D-to-2D adapter now have their first real-data import in addition to synthetic controls; label semantics, independent cohort definition and external scoring remain pending.
The data pipelines, first model baselines, local viewer, review/export workflows and technical input checks are implemented. The combined-intensity policy failed screening; a narrower contrast-only policy passed the same development gates across three seeds. The viewer model remains unchanged pending independent evaluation.

```text
Historical unmeasured platform estimate: superseded by stage/evidence tracking
Tumor classification data [####################] Complete
First tumor classifier   [####################] Complete
First tumor segmenter    [####################] Complete
```

The five readiness gates are: development-pair geometry audit; per-channel
normalization; joint cropping; two-channel model/inference support; and real GPU
forward/backward smoke check. Full training and comparative evaluation have now
also completed. This does not complete the broader multi-specialist fusion system.

| Area | Actual state |
|---|---|
| GPU environment and datasets | ISLES and BRISC v6 images downloaded and audited; UCSF-PDGM v5 metadata plus all 20 pilot T1c MRI/mask pairs acquired |
| DWI training and lesion evaluation | Implemented; two controlled experiments |
| DWI + ADC input pipeline | Implemented and readiness-tested |
| Full DWI + ADC training/comparison | Complete; first fusion model underperformed DWI baseline |
| Tumor dataset | Frozen image-group partitions; near-binary mask conversion documented and tested |
| Tumor image classifier | First baseline trained and evaluated; accuracy 82.82%, macro F1 0.8228 |
| Tumor segmentation | First baseline trained; mean original-size validation Dice 0.6699 |
| Further datasets and specialists | Planned |
| Technical input-quality checks | Implemented before inference; modality verification remains manual |
| Augmented classifier experiment | Five epochs complete; contrast robustness improved with clean/per-class tradeoffs; viewer model unchanged |
| Development robustness | Tumor classifier tested on 943 validation images under six conditions; segmentation/DWI pending |
| Uncertainty and external evaluation | External source review and 2D overlap auditor implemented and control-tested; independent cohort acquisition/scoring and uncertainty remain pending |
| Upload website, backend and interactive viewer | Local prototype implemented; public deployment pending |
| Background jobs and saved-result history | Implemented locally with SQLite persistence |
| Local human review | Saved notes, slice links, history and JSON export implemented |
| Research reports | Offline HTML and JSON snapshots implemented |
| Collaborative review and deployment | Planned |

Latest validated DWI model: mean Dice 0.3607 and component recall 24.6% on 37
development validation studies. These are model metrics, not project completion.
The evaluated fusion model reached Dice 0.3103 and component recall 16.94%, so
DWI-only remains the stronger development baseline. The holdout remains unused.

BRISC partitions: 3,533 train, 943 validation, 990 test and 534 quarantined images.
These are image groups, not patient-independent partitions. The compact tumor CNN
completed five epochs; the tumor segmenter also completed five epochs on 2,691
annotated training images and 721 validation images. Test images remain unused.
Latest: UCSF-PDGM metadata intake completed: 501 exams, 495 patients, six follow-ups grouped, and 296 patients with BraTS mappings. A deterministic 20-patient import pilot and synthetic-tested volume checks are implemented. Pilot MRI acquisition is complete: 20 of 20 pairs imported; the full UCSF cohort remains unacquired. The former transfer blocker is resolved. No independent evaluation has occurred. Next: review real-volume alignment and resizing loss, verify target labels, then freeze a separate evaluation protocol. See `PDGM_FIRST_IMPORT.md`. See `PDGM_INTAKE.md`, `EXTERNAL_DATA_READINESS.md` and `CONTRAST_EXPERIMENT.md`. See `TUMOR_BASELINE.md` and
`TUMOR_SEGMENTATION.md` for measured results and limitations.

See `FUSION_READINESS.md` for the input pipeline and `IMPLEMENTATION_STATUS.md`
for the full roadmap.
