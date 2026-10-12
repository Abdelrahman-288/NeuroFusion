# Federated simulation: recovery, communication and evaluation checks

12 October 2026. The expanded **local system checks are complete**. Independent,
untouched-cohort evaluation remains unmet, so the broader federated requirement
stays partial. No protected scans were evaluated and no active model changed.

## Durable round recovery

`src/neurofusion/federated_exchange.py` adds a file-backed exchange around the
existing sample-weighted FedAvg implementation. A round binds its protocol,
round number, base checkpoint, allowed clients and exact training sample counts.

- Client payloads and their checksum receipts persist across coordinator restarts.
- Missing clients prevent aggregation; the coordinator never silently changes
  the participant set or reweights an incomplete round.
- Identical retransmissions are idempotent. Conflicting retries, stale rounds,
  mismatched protocols/base weights, unknown clients and wrong sample counts fail.
- Tensor keys, shapes, dtypes, finite values and nonfloating buffers are checked
  against the base model. Extra message fields and oversized/truncated payloads fail.
- Atomic temporary-file replacement protects complete files. A commit record is
  written only after the global checkpoint is durable. A restart before commit
  reaggregates verified updates; a restart after commit verifies and returns the
  recorded global checkpoint. An interrupted checksum receipt requires a retry.
- A writer lock prevents concurrent writers. A hard process termination can
  leave a lock; inspect the process before manually removing a stale lock.

The checks include changed accepted updates, changed committed checkpoints,
interrupted commit writes, interrupted receipts, reversed arrival order and
blocked concurrent access. They do not simulate every filesystem or hardware
failure and do not assert multi-process training privacy.

## Real model replay

The saved first-round UCSF model was restored. Both clients repeated the
original second-round training with the original seeds (440/441), eight training
patients each, 120×120 slices, one local epoch and the original optimizer rules.
The coordinator was reopened after receiving only client A, rejected premature
aggregation, accepted an identical retry, then received client B.

The aggregate and the result of reopening its committed state both match every
tensor in the original final federated checkpoint **exactly**. This is actual
checkpoint replay, additional to the synthetic failure-injection tests.

## Communication accounting

Measured second-round serialized payload sizes:

| Payload | Bytes |
| --- | ---: |
| Raw tensor storage per model | 124,964 |
| Base checkpoint broadcast to two simulated clients | 275,096 |
| Client A update | 137,996 |
| Client B update | 137,996 |
| Unique client updates combined | 275,992 |
| Base broadcasts plus unique updates | 551,088 |

The intentionally injected client-A retry adds another 137,996 bytes if counting
all simulated model deliveries. Unique-update accounting excludes that retry.
These are local serialization sizes, not measured network bandwidth. They exclude
protocol manifests, receipt files, filesystem/transport headers and encryption
overhead. No real network service or hospital client is exercised.

## Evaluation checks

All four saved arms reproduced every per-patient Dice value, mean Dice and
simulated-client mean on the same four development-validation patients:

| Arm | Mean Dice |
| --- | ---: |
| Centralized | 0.340660 |
| Client A only | 0.282503 |
| Client B only | 0.220025 |
| Federated | 0.400521 |

The audit verifies checkpoint, raw-source, cache and partition hashes; disjoint
client training/validation assignments; exclusion of the protected cohort; and
equal centralized/federated budgets of 4,960 slice draws. Each local-only model
sees half the training data. Metrics retain the original 120×120 scoring grid;
they are not native-grid physical measurements or new-patient performance.

## Evidence and limits

**18 focused tests passed.** The final real replay is recorded in
`experiments/federated-system-verification-002/summary.json`; its `round-2/`
directory retains the base model, accepted payloads, receipts, contract and
committed aggregate. The earlier `-001` run is preserved.

Reproduce with:

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\verify_federated_system.py --output experiments/federated-system-new
```

This remains a single-host, single-dataset simulation. Hashes are integrity
checks, not authenticated institutions or protection against fabricated finite
updates. Secure aggregation, differential privacy, poisoning resistance and
real network recovery are not claimed. The existing untouched-evaluation
prerequisite is not waived or relabeled as complete.
