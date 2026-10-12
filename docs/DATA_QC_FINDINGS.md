# ISLES real-data preparation results

Date: 2026-10-06 (Africa/Cairo).

## Download and automated inspection

The public version 2.3.1 archive was downloaded from Zenodo record 7960856.
Publisher MD5 matched `302ee280373cdd5c190ab763d72a7a50`.
Local SHA256: `f374895e383f725ddd280db41ef36ed975277c33de0e587a631ca7ea7ad45d6b`.
The center metadata file was also downloaded and checksum-verified.

- 250 studies indexed; all passed the implemented image/mask integrity checks.
- All 250 have FLAIR geometry differing from DWI. Fusion must wait for registration.
- The uncurated cohort failed the exact-image leakage audit.

## Duplicate-content finding and conservative exclusion

`sub-strokecase0090` and `sub-strokecase0169` have identical decoded image arrays
for DWI, ADC and FLAIR, while their supplied masks differ. This was observed from
the downloaded data; no assumption about the original patient identity is needed.
Both subjects are excluded from the development manifest pending identity and
annotation review. No source files or labels were modified, deleted or merged.
This conservative choice avoids arbitrarily choosing a preferred annotation.

`experiments/isles-curated-001/quarantine.json` records the duplicate hashes,
affected subjects and hash of the source manifest. The retained 248-study cohort
passes the current exact-copy and declared-identity audit. Near-duplicate detection,
site review and expert annotation review remain outstanding.

## Draft partitions and geometry check

The retained cohort has draft patient partitions: 174 training, 37 validation,
37 internal holdout. They are seeded random partitions, not site/lesion-stratified
or the official challenge test set. Review distributions before freezing them.

The first draft-training study (`sub-strokecase0001`) passed DWI preprocessing
and lossless reference-mask restoration to native geometry. This verifies the
transform implementation on that study; it is not a trained-model result.

## Local artifacts

- `experiments/isles-qc-002/`: original full manifest, summary and failed leakage audit.
- `experiments/isles-curated-001/`: curated manifest, draft splits and passing audit.
- `experiments/isles-preview-001/index.html`: eight selected real DWI/reference-mask previews.
- `experiments/real-preprocessing-001/`: transformed study and round-trip evidence.
- `experiments/synthetic-overfit-001/progress.html`: separate synthetic GPU training curve.

Selected previews were inspected for render/alignment plausibility only. They are
not a radiologist's adjudication or full-volume annotation review. Subsequent
small real-data training runs are documented separately in `BASELINE_RUN.md`.
