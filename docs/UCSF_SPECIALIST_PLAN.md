# Dedicated UCSF segmentation specialist: engineering baseline

2026-10-08. Protocol: configs/ucsf_specialist_protocol.json. Immutable plan snapshot
and hashed source manifest: experiments/ucsf-specialist-plan-001.

A new randomly initialized 2D U-Net will learn the supplied annotation foreground
(numeric labels 1, 2, 4 combined). This target is an exact numeric contract; it does
not require claiming confirmed ET/TC/WT meanings. Clinical label interpretation
remains pending. No existing BRISC checkpoint or output label is repurposed.

Deterministic patient hashing produces 16 training patients and 4 development
validation patients, including all exams of each patient in the same role. The
salt and assignments are persisted. No test cohort is created. All 20 patients
have already been used for import and preprocessing QA, so even patient-disjoint
validation here remains development validation rather than external evaluation.

| Role | Patients | Slices | Foreground slices | Empty slices |
|---|---:|---:|---:|---:|
| Training | 16 | 2480 | 1015 | 1465 |
| Development validation | 4 | 620 | 250 | 370 |

Planned input: T1c only, canonical RAS axial slices, 240x240, nonzero-volume p1/p99
normalization. Retain every slice; no mask-guided cropping or positive-slice-only
selection. Multi-contrast annotations may contain information unavailable in T1c;
this limits the single-channel baseline and motivates later multimodal work.

Planned model/training: U-Net channels 8/16/32, one binary output, seed 42, five
epochs, batch 8, Adam 0.001, BCE plus soft Dice, mixed precision, no augmentation.
These are initial engineering choices; loader and GPU-memory smoke tests must
succeed before the run. Record any amendments before training. Keep all epochs;
use the final epoch for the first comparison to avoid choosing the best reported
metric after the fact. Predictions must be reconstructed to native grids and
compared with original numeric-union references at threshold 0.5. Report per-patient
metrics and explicit empty-case denominators. No medical-readiness claim follows.

Implemented now: strict numeric-target conversion, deterministic patient-role
assignment, source hash checks for all 40 files, per-role slice inventory and
training protocol. Training loader, specialist model run and native-volume
validation remain next steps. No optimizer updates or new checkpoint exist yet.

The previous clinical evaluation gate remains intact. An engineering baseline on
numeric masks does not resolve expert anatomical review, semantic confirmation,
source independence or external clinical performance. Overall estimate stays ~83%.

Validation: **187 tests passed** in 34.77 seconds, including seven new checks for patient grouping, ordering invariance, empty-slice retention and invalid target/partition rejection.
