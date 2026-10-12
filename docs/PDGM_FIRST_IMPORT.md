# First real UCSF-PDGM import

Completed 2026-10-08. IBM Aspera is installed and both files for the preselected
development-pilot exam `UCSF-PDGM-0200` were transferred from TCIA's official
UCSF-PDGM Version 5 package. This completes one of 20 pilot imports (5%).

## Files and reproducible evidence

- Original T1c MRI: `data/raw/ucsf-pdgm-v5/UCSF-PDGM-0200/UCSF-PDGM-0200_T1c.nii.gz` (2,998,702 bytes).
- Original mask: `data/raw/ucsf-pdgm-v5/UCSF-PDGM-0200/UCSF-PDGM-0200_tumor_segmentation.nii.gz` (53,039 bytes).
- Manifest with source checksums: `data/ucsf-import-manifest.json`.
- Transfer provenance: `experiments/pdgm-import-001/download-provenance.json`.
- Import summary: `experiments/pdgm-import-001/summary.json`.
- Review preview: `experiments/pdgm-import-001/index.html`.
- Prepared arrays and geometry: `experiments/pdgm-import-001/UCSF-PDGM-0200/`.

Original files are retained. Source: [TCIA UCSF-PDGM](https://www.cancerimagingarchive.net/collection/ucsf-pdgm/),
Calabrese et al., UCSF-PDGM, version 5, DOI 10.7937/tcia.bdgf-8v37, CC BY 4.0.

## Checks and remaining review

The image and mask both have shape 240 x 240 x 155, matching affines, 1 mm voxel
spacing and finite values. Canonical orientation conversion and the existing
adapter produced 155 slices at 128 x 128. Numeric mask IDs are 0, 1, 2 and 4;
their semantic meanings have not yet been verified against the versioned source.
Preview overlays are technical QA, not expert annotation review.

Nearest-neighbor downsampling removes numeric label 2 from canonical slice 123
(zero-based). The geometry record preserves this warning. Do not silently drop
this slice, fill in labels, or treat the resized mask as native-resolution truth.
The source mask remains available for native-grid evaluation once the evaluation
protocol and target mapping are defined. The warning detects an absent label on
a slice; it does not quantify every small component lost during resizing.

Import status is `prepared_requires_review`: 1 prepared, 0 failed and 19 awaiting
files. `evaluation_ready` and `model_inference_performed` are both false.
No classifier, segmentation model, checkpoint or viewer score was changed.

## Next gates

1. Acquire the other 19 preselected image/mask pairs and record their checksums.
2. Verify version-specific label meanings and define the intended segmentation target.
3. Review real-volume alignment and resolution loss; retain native masks for scoring.
4. Establish patient/source separation, including BraTS mappings and development use.
5. Freeze a separate evaluation cohort, preprocessing, checkpoint and metrics before scoring.

This glioma cohort cannot establish four-class tumor accuracy or general brain
screening performance. The pilot is for import development, not a frozen test set.
