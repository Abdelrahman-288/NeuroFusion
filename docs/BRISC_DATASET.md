# BRISC tumor dataset

Latest status: both classification and segmentation baselines are trained. The
mask-policy gate described in the historical audit below was resolved by the
observed intensity gap (0-10 versus 246-255), documented threshold 128 and runtime
checks. See `TUMOR_SEGMENTATION.md` for the completed experiment; original masks
were preserved.

Retrieved 2026-10-06 from the author-linked Kaggle release, version 6.

- Source: https://www.kaggle.com/datasets/briscdataset/brisc2025
- Paper: https://doi.org/10.1038/s41597-026-06753-y
- Citation: Fateh et al., BRISC: Annotated Dataset for Brain Tumor Segmentation
  and Classification, Scientific Data (2026).
- Kaggle release metadata declares Attribution 4.0 International (CC BY 4.0).
  Preserve attribution, source notices and record transformations.
- Archive: `data/downloads/brisc-v6/brisc-v6.zip`, 262,284,213 bytes.
- Local archive SHA256: `edc2295d0eb6be19aa4ecee74974db0efbb5e088ddcdfde5229e3e2bfb0d010b`.
  This hash is locally calculated, not a publisher-provided archive digest.
- ZIP CRC checks passed. Publisher manifest and per-file SHA256 checks are
  implemented in `scripts/audit_brisc.py`.
- Unmodified source files: `data/raw/brisc-v6/brisc2025/`.
- Retrieval/license evidence: `data/downloads/brisc-v6/provenance.json` and
  `kaggle-metadata.json`.

## Scope and split limitations

This is 2D image data, not volumetric MRI or a brain atlas. Proposed uses are a
four-class image classifier and a binary tumor-mask specialist. The classification
and segmentation folders repeat many of the same images: they must share partitions
and must not be counted as independent evidence.

The publication states that complete subject independence cannot be guaranteed.
Image filename indices must not be treated as patient identifiers. The no_tumor
class includes non-neoplastic abnormalities, so it must not be renamed healthy.
BRISC reuses source collections that may overlap other Kaggle datasets discussed
in this project. Do not use those as independent external tests without an audit.

The local audit checks file checksums, decoded images, binary masks, image-mask
dimensions, task-copy consistency, exact image duplicates, and cross-source-split
perceptual-hash candidates. Similarity candidates require review; they are not
proof of patient identity. Auditing supplied test files is data-quality inspection,
not model evaluation; no tumor model has been trained or scored.

## Reproduce

```powershell
Set-Location D:\NeuroFusion
& .\.venv-neurofusion\Scripts\python.exe scripts/download_brisc.py
& .\.venv-neurofusion\Scripts\python.exe scripts/audit_brisc.py --root data/raw/brisc-v6/brisc2025 --output experiments/brisc-audit-002
```

The downloader refuses to overwrite an existing extracted dataset. Audit output
must be a new directory. Original train/test memberships remain preserved.
Next gate: review similarity candidates, establish an explicit image-level split
policy, and then implement the tumor baseline. Patient-level generalization will
remain unproven even after exact duplicates are removed.

## Completed audit and classification curation

The initial strict audit rejected all 4,793 masks for intermediate grayscale
values. They are not assumed corrupt: the follow-up audit verified every mask
against the publisher SHA256 and dimensions. Threshold-128 foreground counts are
saved for inspection, but no thresholded target files were created. Segmentation
training remains pending an explicit mask-encoding policy.

The classification audit verified 6,000 images. It found 134 classification
exact-duplicate groups, including 98 groups crossing the supplied source split.
There were 321 cross-source-split perceptual-similarity candidate pairs; similarity
does not establish that two images belong to one patient.

The conservative curation groups all 6,000 images by exact decoded pixels and
63-bit DCT-hash distance at most four, using transitive connected groups. It
quarantines groups with conflicting labels and training members of any group
touching the source test split. Remaining groups receive a deterministic roughly
80/20 train/validation assignment (seed 42; actual counts depend on group sizes).
All source files and original memberships are retained.

| Partition | Images |
|---|---:|
| Train | 3,533 |
| Validation | 943 |
| Test | 990 |
| Quarantine | 534 |

There are 4,891 groups and 19 label-conflict groups. All retained groups are
partition-disjoint. The 534 exclusions include conservative similarity candidates,
not only proven duplicate images. These are image-level research partitions,
not an official BRISC benchmark split or proof of patient independence. The
source test was inspected for leakage, not used for model selection.

Evidence: `experiments/brisc-curated-001/summary.json`, `splits.json`,
`groups.json`, `similarity-edges.json`, and `mask-audit.json`. The first audit is
preserved at `experiments/brisc-audit-001/`. The project suite has 48 passing tests.

Next: a four-class tumor image classifier on the frozen training/validation
partitions. Preserve the test partition for final model evaluation. No tumor
model or tumor performance result exists yet.
