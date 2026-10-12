# Final evaluation readiness

12 October 2026. Final evaluation is **not complete**. The latest eligibility
audit found zero models cleared for final independent evaluation under the
project's existing prerequisites. No protected inference was performed.

## Work completed

- Finalized version-1 engineering targets for tumor classification, tumor
  segmentation, DWI stroke, UCSF numeric foreground, matched DWI/ADC fusion,
  EEG events and the federated segmentation simulation.
- Bound the definitions, qualification records, existing split files and
  branch-specific evidence by SHA-256 in a new immutable-by-hash snapshot.
- Recorded supported inputs, numeric labels, thresholds, metric definitions,
  statistical reporting plan and the conditions required before execution.
- Tested fail-closed eligibility: missing/failed prerequisites, an empty cohort
  of eligible models and an unfrozen protocol cannot authorize evaluation.
  **Seven focused tests passed.**

Target definitions are frozen engineering conventions, not human-certified
clinical label meanings. UCSF foreground is explicitly the numeric union
`{1,2,4}`; no clinical compartment interpretation is asserted. This resolves
the target-definition writing task without claiming the entire UCSF signed
qualification contract passed.

## Eligibility dispositions

| Branch | Unresolved prerequisite |
| --- | --- |
| BRISC classifier/segmenter | Verified patient independence absent; reused development calibration and positive-only segmentation do not establish final screening eligibility. |
| DWI stroke | Candidate development checks fail because of new zero-overlap cases; no justified final acceptance package is ready. |
| UCSF specialist | Reproducible development performance remains insufficient; source/exposure limitations are documented but not certified absent. |
| Fusion | No improved fusion candidate passed comparison requirements; DWI fallback is not a qualified fusion candidate. |
| EEG | No untouched recordings remain within the 12-recording pilot; excessive false alarms remain. |
| Federated simulation | Engineering replay passed, but reused four-patient evaluation and lack of a qualified UCSF candidate do not satisfy untouched evaluation. |

The eligibility booleans are conservative audit dispositions: `false` means
the complete prerequisite has not been demonstrated, not that every component
experiment failed. Passing engineering tests or selecting an unchanged baseline
cannot replace the missing evidence.

## Protocol state and remaining work

`experiments/final-evaluation-readiness-001/targets.json` is the frozen target
definition artifact. `protocol-readiness.json` remains explicitly
`BLOCKED_NOT_FROZEN_FOR_EXECUTION`. No checkpoint/cohort acceptance protocol is
declared frozen while the existing gates fail. No arbitrary clinical acceptance
cutoffs were invented to make models eligible.

To proceed, a branch needs demonstrated development eligibility, a compatible
cohort with defensible independence claims, a single checkpoint/preprocessing
binding and justified task-specific acceptance criteria. Then the executable
protocol can be frozen before first inference. Test results must not be used to
choose thresholds, checkpoints or patients. Existing data-only and optional
expert-review constraints remain unchanged.

This task cannot honestly be closed by evaluating an empty eligible set, using
development data again as an untouched test, or changing failed gates to true.
The snapshot records the reason for each exclusion and preserves protected
data for an eligible evaluation.
