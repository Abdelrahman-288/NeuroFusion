# Measurements, coordinates and linked evidence

Completed 11 October 2026 for the supported tumor-image and stroke-DWI application paths.

## Implemented behavior

- DWI predictions include total and connected-region volumes in mL, calculated as foreground voxel count times the absolute determinant of the voxel-to-world affine divided by 1000. This handles anisotropic, oblique and sheared grids without substituting the product of axis lengths for the determinant.
- Each predicted region includes a count, index-space bounding box, centroid, representative slice and an anchor inside that region. DWI centroids include canonical voxel coordinates, original voxel coordinates and NIfTI RAS+ world millimeters. These are not atlas or named anatomical locations.
- DWI uses 26-connected components; tumor images use 8-connected components. No component is silently discarded. IDs are local to that result and do not track a lesion across scans.
- Tumor PNG/JPEG predictions are measured on the original image grid after probability resizing. They report pixels only. No physical area, volume or millimeter coordinates are inferred from absent spacing.
- Finding buttons in the viewer select the corresponding slice. Offline reports link each region to an embedded preview, including all slices referenced by findings. The JSON also records the anchor's preview row and column.
- Each finding is bound to the input hash, model hashes, probability-file hash and its image/overlay hashes. Inference verifies the measurements before saving. HTML export recomputes them and rejects changed prediction files, mismatched links, incorrect coordinates or altered previews.
- Earlier results are explicitly marked as having no recorded validated measurements. They are not retroactively changed.

## Geometry contract

Indices are zero-based voxel centers. The NIfTI affine maps canonical indices to RAS+ world millimeters; the inverse original affine maps world coordinates to original indices. Canonicalization is axis permutation and flipping only, with no spatial interpolation or anatomical registration. The canonical and original affines, shapes and inverse orientation must agree.

The current DWI viewer uses `np.rot90` on each canonical axial array: a voxel `(i,j,k)` appears at preview row `Y-1-j`, column `i`, slice `k`. The representative slice maximizes that component's predicted area, and its anchor is an actual component voxel nearest its centroid in that slice. A centroid itself can lie outside an irregular region.

Unknown units, inconsistent transforms, singular/nonfinite affines and malformed probabilities are rejected. Rendered previews retain voxel-based proportions; a screen distance is not a physical distance. Diameters, clinical lesion boundaries, atlas registration and longitudinal correspondence are not asserted.

## Verification

- **77 focused tests passed**, covering measurements, preprocessing, inference, reports and viewer API behavior.
- Synthetic cases cover all **48 axis permutations/flips**, anisotropic spacing, translation and a sheared affine. Known foreground volumes, orientation restoration, coordinate round trips, threshold boundaries and preview anchors were checked.
- **37 existing ISLES validation volumes / 290 predicted components** passed original-versus-canonical volume conservation and coordinate checks. Maximum index round-trip error was `2.84e-14` voxels.
- Fresh real inference passed for a BRISC training image and an ISLES training volume: **6 tumor regions and 13 stroke regions**, with valid source/overlay links. No protected holdout inference occurred.
- Report tests check working anchor targets, pixel-only labeling, and rejection of changed evidence. The viewer JavaScript passed syntax checking; visual browser interaction was not part of this verification.

Evidence: `experiments/measurement-verification-001/summary.json` and `cases.json`; fresh outputs and operational checks are in `experiments/measurement-integration-001/`.

## Scope of completion

The requested numerical measurement, supported coordinate-transform and finding-link validation is complete. Correct geometry does not make an inaccurate predicted mask a correct anatomical measurement. Independent clinical measurement accuracy remains unestablished. No models were replaced and no datasets were downloaded.

Running servers must load the updated inference code before creating results with these fields. Existing result files remain unchanged.
