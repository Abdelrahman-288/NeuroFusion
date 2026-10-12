# UCSF-PDGM pilot acquisition complete

2026-10-08. The original deterministic 20-exam development pilot is fully acquired:
20 T1c MRI volumes plus 20 tumor-mask volumes from official UCSF-PDGM version 5.
Batch 004 added the remaining 13 pairs. This is not the entire 501-exam collection.

**20/20 prepared; 3,100 slices; 0 import failures; 0 awaiting files.**
All exams remain prepared_requires_review. Ten exams have slice-level label-loss
warnings affecting 19 slices at 128 pixels. Original reference masks are retained.
Absence of slice-level warnings does not guarantee small-component preservation.

Evidence: experiments/pdgm-import-004/summary.json and per-exam geometry/arrays.
Cumulative source manifest: data/ucsf-import-manifest.json. Provenance for each
acquisition batch remains in pdgm-import-001 through pdgm-import-004. Files were
obtained through TCIA's official Aspera package; CC BY 4.0 attribution continues
in the dataset registry and first-import report. All hashes are local checksums,
not publisher signatures. Original downloaded files have not been removed.

Validation: complete source NIfTI decoding, finite values, explicit numeric-label
checks, matching image/mask geometry, patient/pilot identities, all 40 source-file
SHA-256 checks and all 20 prepared-archive checksums passed. No code changed;
the latest previous full regression remains 152 passed.

## Remaining gates

1. Confirm version-specific numeric label semantics and define target mapping.
2. Review real-image alignment and extend component/resolution QA across the pilot.
3. Establish source/patient independence, including BraTS mappings and development use.
4. Freeze a separate evaluation protocol: cohort, checkpoint, preprocessing,
   reconstruction, native reference masks and metrics, before model scoring.

No model inference, external scoring or model promotion occurred. The development
pilot must not be relabeled as an untouched test cohort. Overall platform scope
estimate is approximately 83%; pilot acquisition is 100%. Neither is clinical readiness.
