# UCSF specialist engineering baseline

Completed 2026-10-08. Run: `experiments/ucsf-specialist-train-002`.

Randomly initialized 31,241-parameter 2D U-Net trained for five epochs on 16 patients (2,480 slices), using T1c MRI at 240 x 240. Four separate development-validation patients (620 slices) were reconstructed onto their original MRI grids. The target is the supplied numeric annotation union of IDs 1, 2 and 4; it is not a certified clinical region definition. All 20 patients had previously participated in preprocessing development.

Final epoch was chosen before training. Mean native-volume Dice: **0.426704**; IoU: **0.315932**; mean absolute volume error: **32.24275 mL**. Dice by patient: 0038 = 0.73825, 0172 = 0.66861, 0194 = 0.29996, 0274 = 0.00000. All four predicted volumes were smaller than their reference volumes. The last case had 548 predicted voxels but zero annotation overlap. These scores indicate substantial under-segmentation and uneven performance.

Training losses: 1.23552, 0.95128, 0.84951, 0.80393, 0.73244. Development Dice: 0.00000, 0.41372, 0.44858, 0.43256, 0.42670. Falling training loss did not consistently improve validation agreement. Epoch three is not retrospectively substituted for the predeclared final result.

All five checkpoints and four final original-grid NIfTI predictions are retained. Protocol, partitions, cache manifest, code snapshots and SHA256 provenance accompany the run. A reload of the final checkpoint reproduced all four metric dictionaries and masks exactly. 192 tests passed, including native reconstruction with flipped axes and explicit undefined-case aggregation. See verification.json for optimizer update and mixed-precision overflow counts.

Attempt 001 stopped before checkpointing because the initial runner incorrectly raised on a recoverable AMP overflow. Attempt 002 restarted from seed 42, allowing GradScaler to skip overflowing updates and lower its scale. The failed attempt is retained with its reason. The successful run took about 69 seconds on the RTX 4070 Laptop GPU; peak PyTorch allocation was 344.85 MiB, not total GPU memory.

This is development engineering evidence, with no independent test cohort and no clinical performance claim. T1c alone lacks information present in multi-contrast annotations. Existing application models were not replaced.

Next stage: inspect final predictions against annotations in all three planes, quantify missed components and false positives, then define a controlled improvement experiment. Do not repeatedly tune these four patients and call them an independent test set. Broader dataset/model expansion, independent evaluation and expert review remain outstanding.

Overall implementation estimate: approximately 85%; a rough scope estimate, not measured effort or diagnostic readiness.
