# UCSF-PDGM acquisition batch 002

2026-10-08. Downloaded the official version-5 T1c MRI and tumor segmentation
files for preselected pilot exams UCSF-PDGM-0019 and UCSF-PDGM-0025 using Aspera.
Original downloads are retained; verified copies are under data/raw/ucsf-pdgm-v5.

Cumulative import: **3/20 exams (15%), 465 slices, 0 failed, 17 awaiting files**.
The cumulative manifest is data/ucsf-import-manifest.json. Import summary,
per-case geometry and arrays are in experiments/pdgm-import-002. Source provenance
for this batch is download-provenance.json there; the first case provenance stays
in pdgm-import-001. Hashes are locally computed, not publisher-provided.

0019 and 0200 each have one slice losing a numeric mask ID at 128 pixels; 0025
has no slice-level warning, which does not establish component preservation.
All three remain prepared_requires_review. Numeric label semantics, real alignment
review and source independence remain pending. Native reference masks are retained.
No model inference, external scoring or checkpoint promotion occurred.

Checks: complete NIfTI decoding, finite values, image/mask geometry, allowed numeric
IDs, source/copy checksums, pilot identity validation and successful importer run.
No code changed; previous regression remains 152 passed.

Next: acquire the remaining 17 selected pairs, extend resolution QA, verify labels,
and freeze a separate patient/source-independent evaluation protocol. Overall
platform estimate remains approximately 81%, not a measure of clinical readiness.
