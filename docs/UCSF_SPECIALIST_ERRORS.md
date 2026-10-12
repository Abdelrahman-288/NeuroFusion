# UCSF specialist error review

Completed 8 October 2026. Final checkpoint from `ucsf-specialist-train-002`, threshold 0.5. All four saved original-grid masks were checked against their recorded metric dictionaries and original source hashes.

## Findings

| Exam | Reference components without overlap | Predicted components without overlap | Missed voxels | Extra voxels |
|---|---:|---:|---:|---:|
| UCSF-PDGM-0038 | 0/1 | 0/2 | 79,347 | 15,690 |
| UCSF-PDGM-0172 | 4/6 | 8/9 | 75,427 | 45,855 |
| UCSF-PDGM-0194 | 1/2 | 1/5 | 24,242 | 594 |
| UCSF-PDGM-0274 | 1/1 | 2/2 | 12,642 | 548 |

Six of ten connected annotation regions have no overlap, and eleven of eighteen predicted components have no annotation overlap. Components use 26-connectivity with a permissive any-voxel overlap rule. These are geometric region counts, not clinically verified lesion detections; no size filter is applied. Four missed components in 0172 contain only 7, 2, 1 and 2 voxels. The missed components in 0194 and 0274 contain 7,339 and 12,642 voxels respectively. Report sizes alongside counts to avoid giving tiny components the same interpretation as large ones.

All four cases under-predict total annotation volume. The error-focused views show partial annotation coverage in the first three cases and no annotation overlap in 0274. This is technical visual review, not expert anatomical approval. Some extra predictions coexist with substantial under-segmentation.

## Review artifact

`experiments/ucsf-specialist-errors-001/index.html` contains 48 views: three fixed fractions and the maximum missed-voxel plane on each of three canonical axes per patient. Green = overlap; red = missed annotation; amber = extra prediction. Error-focused slices use the reference and deliberately highlight failures; they are not representative random samples. Overlays can be hidden to inspect the MRI. Sparse views cannot replace whole-volume review.

Native image pixels and physical aspect are retained. Source MRI, annotations and prediction hashes, complete component sizes, overlap fractions, and false positives on annotation-empty axial slices are recorded in summary.json. The 12 error-focused views were inspected in preview.png. No clinical region semantics or independent test claim is introduced.

Validation: 194 regression tests passed, followed by all eight viewer API tests after extending route coverage. New tests check partial overlap, missed and extra components, diagonal connectivity, empty masks and invalid inputs.

Both the training summary and this report are linked in the local viewer. Updated server routes allow only named JSON/HTML artifacts and the four cases' PNG assets. Two report pages and 101 linked assets passed HTTP checks; checkpoint and traversal paths remain unavailable. Restart a previously running viewer server to load the new routes.

## Next controlled experiment

`configs/ucsf_balanced_sampling_protocol.json` records a planned 50/50 annotation-positive/empty training-slice sampler with replacement and 2,480 draws per epoch. Current uniform slice sampling exposes about 40.9% positive slices. This single change tests an exposure hypothesis; the error audit does not prove sampling caused the failures. Keep the same seed, partition, architecture, initialization, five epochs, loss, optimizer, threshold and final-epoch selection. Validation stays complete and unsampled.

Accept only as a development candidate if mean Dice increases, mean IoU does not decrease, mean false-positive volume does not increase, and no patient's Dice decreases by more than 0.05. If it passes, confirm with paired seeds before any promotion decision. If it fails, retain the baseline and report the negative result. These rules were recorded before running the experiment; training has not started. Four repeatedly reviewed development patients cannot establish independent performance.

Overall implementation estimate stays approximately 85%. This stage improves evaluation and review capability; it does not demonstrate improved model performance. Remaining work includes controlled improvements, broader datasets/model integration, independent evaluation and expert review.
