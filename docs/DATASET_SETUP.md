> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# First real dataset: ISLES 2022

The first download and automated audit are complete. See `DATA_QC_FINDINGS.md`
before proceeding: two duplicate-content subjects are quarantined and the
248-study development manifest is in `experiments/isles-curated-001/`.
The steps below describe the reproducible preparation process.

1. Read the release at https://zenodo.org/records/7960856 and paper at
   https://www.nature.com/articles/s41597-022-01875-5. Record the applicable terms,
   release version, download date and checksums in your local provenance record.
2. Obtain the public training release and extract under `data/raw/isles-2022/`.
   The public CC-BY-4.0 release has been downloaded and checksum-verified locally.
3. Inspect the actual release structure. Prepare a CSV using
   `configs/study_index.example.csv` as the column schema. Each row describes one
   patient study with DWI, ADC, FLAIR and a binary mask. Use source patient identifiers.
   Do not rename subjects per slice. Repeated studies retain the same subject ID.
4. Verify sequence identity visually and from metadata. A filename is not proof.
   This first importer expects 3D NIfTI files and a mask on the DWI grid. It does
   not extract volumes from 4D acquisitions or perform registration automatically.
5. Run the manifest, split and audit commands in README. Different ADC/FLAIR
   geometry is recorded as a warning and must be resolved before fusion training.
6. Inspect representative images and masks manually, including negative/empty
   masks. The automated checks do not prove anatomy, label correctness or de-identification.
7. Freeze approved patient partitions before patches are extracted. The initial
   random splitter is a reproducible development baseline, not site/lesion
   stratification. Review cohort distribution before adopting it for experiments.

No real-data quality gate is complete until these steps have been performed.
The current exact-copy detector does not find all near-duplicates, image rotations,
patient aliases, or overlaps between independently named collections.
