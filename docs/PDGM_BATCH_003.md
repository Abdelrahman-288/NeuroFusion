# UCSF-PDGM acquisition batch 003

2026-10-08. Four official version-5 T1c MRI/tumor-mask pairs acquired using Aspera:
0038, 0061, 0080 and 0085, all preselected in the original pilot. Original downloads
are retained and verified copies stored under data/raw/ucsf-pdgm-v5.

Cumulative: **7/20 exams (35%), 1,085 slices, 0 failures, 13 awaiting files**.
Manifest: data/ucsf-import-manifest.json. New source provenance, immutable import
summary, geometry records and arrays: experiments/pdgm-import-003. Original batch
001/002 reports remain historical snapshots. Hashes are locally computed.

Five exams have slice-level label-loss warnings at 128 pixels: 0200 (1), 0019 (1),
0061 (7), 0080 (1), 0085 (1). This totals 11 slices. 0025 and 0038 have no slice-level
warning; this does not establish preservation of tiny disconnected components.
All seven remain prepared_requires_review, with original reference masks retained.

Validation: complete source decoding, finite values, allowed numeric IDs, matching
image/mask geometry, source/copy SHA-256, pilot identity checks, importer success
and prepared-archive checksum verification. No code changed; the previous full
regression remains 152 passed. No model inference or external scoring occurred.

Next: acquire the remaining 13 pairs; extend component/resolution QA, verify
version-specific label meanings and alignment, then freeze a separate evaluation
protocol with patient/source independence. Overall scope estimate remains ~81%.
