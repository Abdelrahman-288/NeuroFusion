# Model promotion and rollback

Implemented local registry controls on 10 October 2026. Existing pinned models
remain active. No research candidate has been promoted and no failed quality
check has been waived. Downloads remain disabled.

## Behavior

`configs/model_registry.json` is created only after an accepted promotion. When
absent, the application uses its original three pinned checkpoints. The first
registry revision records that baseline. Subsequent promotions and rollbacks
append numbered, hash-linked revisions. An exclusive writer lock and an atomic
file replacement prevent overlapping writers and partial JSON updates. A crash
can leave a lock file: inspect it and the process before removing a stale lock.

The predictor captures the active model map on first model load and keeps it
for its lifetime, so one running job cannot mix registry revisions. A new server
process is required to adopt changes. Result provenance records the actual
loaded checkpoint hashes. Promotion does not restart the running viewer.

Rollback requires an earlier recorded revision, checks its checkpoint hashes,
and appends a new revision rather than erasing history. Packaging includes all
recorded checkpoints needed for rollback; private training/evaluation evidence
is retained in the project and is not automatically copied into the code bundle.

## Acceptance contract

The candidate report must identify one supported model key, threshold 0.5,
training partition `train`, and `protected_data_used: false`. A different
threshold or architecture needs explicit inference integration before promotion.
The report binds checkpoint, protocol, training manifest and evaluation using
project-relative `path` and `sha256` records. Files outside the project are
rejected. Checkpoints must load with the supported architecture and safe loader,
and all weights must be finite.

All seven `checks` must be literal JSON `true`: `development_quality`,
`independent_evaluation`, `input_compatibility`, `uncertainty`, `robustness`,
`prediction_reproduction`, and `regression_review`. The separately hash-bound
evaluation must repeat the checks, `model_key`, and `checkpoint_sha256`.
Absent or failed checks reject the update without changing the active registry.

These are local integrity controls, not independent certification: a person
with filesystem access can fabricate a report. Versioned annotation and retraining
integration is now implemented. A real BRISC run used 2,691 training cases and
721 validation cases; checkpoint reload reproduced predictions exactly. Its
development quality gate failed, so it is rejected and the baseline stays active.
Do not fill in passing flags to bypass an unresolved scientific requirement.

## Versioned retraining integration (12 October 2026)

`scripts/retrain_versioned.py` freezes the source-label version and supports
parent versions with approved adjudication exports. Export imports must match
training images by hash and cannot change validation/protected partitions.
Training supports the three application architectures, validates every record,
uses the final epoch, records complete train/validation coverage, and saves
checkpoint-bound predictions. The assembler verifies hashes and coverage and
binds supplementary gate evidence to the exact model, protocol and label version.
Missing evidence remains false. Registry acceptance requires schema 2 lineage.

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\retrain_versioned.py freeze --model tumor_segmenter --output experiments\labels-NEXT
.\.venv-neurofusion\Scripts\python.exe scripts\retrain_versioned.py train --annotations experiments\labels-NEXT\annotations.json --output experiments\retraining-NEXT --epochs 1
.\.venv-neurofusion\Scripts\python.exe scripts\retrain_versioned.py assemble --run experiments\retraining-NEXT\training-run.json --output experiments\acceptance-NEXT
```

The real run is `experiments/versioned-retraining-001`; its acceptance bundle is
`experiments/versioned-retraining-acceptance-001`. Source labels are publisher
labels, not newly approved human reviews. Synthetic tests exercise approved
exports, all three training architectures, genuine acceptance conditions and
rollback in temporary registries; they do not certify any real candidate.

## Commands

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\manage_models.py status
# Only with genuine passing, checkpoint-bound evidence:
.\.venv-neurofusion\Scripts\python.exe scripts\manage_models.py promote --report experiments/candidate/promotion.json --expected-revision -1
# After the first promotion (revision 1), restore baseline (revision 0):
.\.venv-neurofusion\Scripts\python.exe scripts\manage_models.py rollback --revision 0 --expected-revision 1
```

The expected revision prevents overwriting a newer decision based on stale
state. `-1` means no registry exists yet. No automatic promotion is performed.

## Verification

Tests cover passing promotion and rollback, every failed gate, changed evidence,
protected training, mismatched evaluation, path escape, concurrent-writer locks,
history corruption, interrupted replacement, nonfinite weights and predictor
snapshot retention. Tests use temporary models and synthetic evidence, which
do not qualify any real candidate.

Full regression verification: **311 tests passed** in 69.80 seconds. Operational
verification at `experiments/model-registry-acceptance-001/summary.json` loaded
all three original models, exercised tumor and stroke inference on existing
training inputs, and checked stroke output geometry. No protected-cohort
inference was performed. The model status command confirms the original pinned
checkpoints remain active and no promotion history has been created.
