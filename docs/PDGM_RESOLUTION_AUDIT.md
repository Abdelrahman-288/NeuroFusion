# UCSF-PDGM annotation resolution audit

2026-10-08. Development exam: UCSF-PDGM-0200. Reproducible results are in
`experiments/pdgm-resolution-001/summary.json`; source hashes are recorded there.
Run `scripts/audit_pdgm_resolution.py --help` for the required image, mask and
fresh output directory arguments.

The adapter samples categorical masks at three sizes, then reconstructs them
onto the original canonical voxel grid using nearest-neighbor interpolation.
This measures annotation sampling loss, not model performance. Model probability
reconstruction remains bilinear and is a different operation.

| Size | Label 1 roundtrip Dice | Label 2 roundtrip Dice | Label 4 roundtrip Dice | Native components without same-label overlap |
|---|---:|---:|---:|---:|
| 128 | 0.9396 | 0.8329 | 0.9049 | 12 |
| 240 | 1.0000 | 1.0000 | 1.0000 | 0 |
| 256 | 1.0000 | 1.0000 | 1.0000 | 0 |

Components use 26-connectivity in 3D, independently per numeric ID. At 128,
one label-1 component and eleven label-2 components have no same-label overlap
after reconstruction. These contain one or two native voxels each; they are
annotation components, not established separate lesions. Partial damage, merges
and boundary changes can occur even for components retaining some overlap.
The prior slice-level warning therefore understated the kinds of loss to review.

## Evaluation policy

- Preserve native masks as reference truth. Do not score against downsampled masks.
- Keep the current model and preprocessing unchanged until a separate protocol
  explicitly defines compatibility, target labels and prediction reconstruction.
- Treat 240/256 results as single-case annotation QA. They neither select a new
  model input size nor establish general resolution safety across the cohort.
- Do not remove difficult slices, invent missing annotations, or promote a model
  based on this import pilot. No inference or external evaluation occurred.

## Label-source review

The archived official [TCIA collection page](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/)
describes three annotation compartments: enhancing tissue, non-enhancing/necrotic
tissue and surrounding FLAIR abnormality. The page also relates annotation to
BraTS 2021. This supports the compartment descriptions but does not by itself
explicitly establish the mapping of numeric IDs in these version-5 files.
The live page returned HTTP 500 during this review. The previously acquired
page and its checksum are retained under `data/downloads/ucsf-pdgm-v5-metadata/`.
No secondary-source mapping was silently adopted; `label_semantics_verified`
remains false. Obtain explicit version-specific mapping before target conversion.

Next: acquire the remaining 19 pilot pairs, confirm label mapping, review real
alignment, then define a separate patient/source-independent evaluation protocol.

Validation: full regression suite passed, **152 tests**, including six new cases covering tiny-component loss with surviving same-label regions, padded identity reconstruction, invalid labels and empty foreground.
