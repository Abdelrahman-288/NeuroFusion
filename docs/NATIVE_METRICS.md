# Native-grid binary segmentation metrics

2026-10-08. Implemented src/neurofusion/native_metrics.py and synthetic checks
in tests/test_native_metrics.py. Evidence: experiments/native-metrics-001.

Inputs must be explicit binary 3D NIfTI masks on matching grids, with millimeter
units and valid affines. Coded qform/sform conflicts are rejected. The function
does not threshold probabilities, guess multiclass mappings, register images or
resample references. Prediction reconstruction and the threshold must be specified
by a later frozen evaluation protocol.

Outputs: voxel confusion counts, Dice, IoU, voxel precision/recall, reference and
predicted foreground volume, signed and absolute volume difference. Physical
volume uses the absolute affine determinant divided by 1000 for milliliters.
These are annotation-comparison quantities, not diagnostic performance measures.

Empty reference and prediction: Dice/IoU are null, not a perfect score. Empty
reference makes recall undefined; empty prediction makes precision undefined.
When exactly one mask is empty, Dice/IoU are zero. A future aggregate must report
empty-case counts and contributing denominators explicitly; no aggregate scorer
is introduced here. Do not compare these conventions with other published metrics
without checking their empty-mask policies.

Synthetic evidence includes known TP=FP=FN=TN=1 with Dice 0.5, IoU 1/3 and
reference volume 0.048 mL at 2x3x4 mm spacing, plus both-empty, false-positive and
missed-foreground cases. Tests also reject fractional probabilities, multiclass
IDs, NaN, translated grids, conflicting headers and unspecified spatial units.

This utility is not yet connected to an external evaluation runner. No real scan
was scored; no model inference or promotion occurred. The UCSF candidate target
contract, anatomical review and patient/source independence remain unresolved.
Next: define compatible targets and reconstruct native-grid predictions under an
approved research protocol before evaluation. Overall rough estimate stays ~83%.

Native-metrics validation: full regression **179 tests passed** in 39.08 seconds, including 10 new metric/geometry cases.
