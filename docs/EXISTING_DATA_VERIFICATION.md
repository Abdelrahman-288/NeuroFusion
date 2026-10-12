# Existing-data release verification — 10 October 2026

The missing datasets and associated specialist branches have been removed from
the current plan. Dataset acquisition scripts are disabled before any network
or acquisition work. No datasets or packages were downloaded in this change.

## Verified

- Full regression suite: **292 passed** in 96.39 seconds.
- All three hash-pinned application checkpoints load using the installed environment.
- Tumor classification, segmentation and preview generation run on an existing
  BRISC training image with its source hash checked.
- Stroke inference runs on an existing ISLES training volume with its source
  hash checked; probability output matches the original shape and physical affine.
- The existing 12 EEG recordings match their recorded checksums.
- The existing protected UCSF cohort's 40 source files match the acquisition
  checksums. No protected-cohort inference or training was performed.
- Local operational results: `experiments/existing-data-acceptance-002/summary.json`.

The four source directories contain approximately 3.08 GB including metadata;
the separately stored protected UCSF subset adds approximately 61.4 MB.
These are existing local files, not required download sizes.

## Remaining acceptance

The revised 19-group tracker contains 6 implemented, 11 partial, 1 pending and
1 planned group. These counts are not effort-weighted percentages.
Candidate promotion/rollback, retained robustness and measurement integration,
model-quality/uncertainty failures, independent-evaluation prerequisites and
deployment acceptance remain open. No model was promoted by this scope change.

Operational checks demonstrate that the current local research application
runs. They do not establish model accuracy, clinical readiness or full project
completion. The official current plan is `docs/CURRENT_PLAN.md`.
