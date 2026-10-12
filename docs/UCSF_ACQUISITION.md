# UCSF provisional acquisition — 9 October 2026

Completed: **20/20 MRI/annotation pairs**, 40 original NIfTI files, from the official UCSF-PDGM version 5 Aspera package 1065. The original label-blind acquisition queue was preserved. The Aspera client was reconnected before downloads; all files were then independently audited locally.

Evidence: `experiments/ucsf-acquisition-001/summary.json`, `provenance.json`, `qualification.json`, and `verification.json`. The report is linked from the local viewer at `/research/ucsf/acquisition/index.html`.

The new copies are isolated under `experiments/ucsf-acquisition-001/raw/<exam>/`. They have not been added to the development manifest, training cache, or deployed model registry. Original downloads remain in the user's Downloads directory.

Checks completed:

- Exact queued filenames, normalized baseline patient identity, metadata membership, no development-patient or recorded BraTS mapping overlap.
- SHA256 before and after audit and after copying; native 3D image/mask shapes and affines, millimeter units, finite nonconstant image data, integer annotation values restricted to 0/1/2/4.
- Exact canonical voxel fingerprints, checked against all 20 development images and within the new queue. No duplicates found. This check does not establish absence of near-duplicates or unknown cross-dataset overlap.
- A separate provenance and inventory snapshot. Checksums were computed locally, not supplied by the publisher.

No model training, inference, target-burden-based selection or clinical compartment interpretation occurred. Automated integrity checks do not replace full-volume expert alignment review. Cohort independence is unverified and the evaluation cohort remains unfrozen.

UCSF research qualification now has **2/10 gates passed**: reproducibility and acquisition integrity. This is not whole-project completion or clinical readiness. Development performance still fails the previously specified confirmation checks. Acquisition stage completion is **100%**.

Next: build an exposure and source-overlap ledger for these patients and prepare a whole-volume alignment-review workflow. Required expert judgments remain for a qualified human reviewer. Keep these cases out of model selection. A development-qualified candidate and a prospectively frozen evaluation protocol are required before held-out inference.

Reproducible intake command (requires a fresh output directory):

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts/audit_ucsf_acquisition.py --downloads C:\Users\abdel\Downloads --output experiments/ucsf-acquisition-002
```

The command deliberately refuses to overwrite earlier output. Do not rerun solely to duplicate a completed audit. Missing, ambiguous, invalid or duplicate pairs do not count as verified. The script audits and copies data; it does not download it or certify independence.

Source and attribution: Calabrese et al. (2022), *The University of California San Francisco Preoperative Diffuse Glioma MRI (UCSF-PDGM), Version 5*, TCIA, [DOI 10.7937/tcia.bdgf-8v37](https://doi.org/10.7937/tcia.bdgf-8v37), CC BY 4.0.
