# Local federated development simulation

**12 October 2026 update:** Expanded recovery, serialized communication and fixed-development evaluation checks are complete. Partial-delivery recovery and committed-round recovery reproduce the original global weights exactly; all four evaluations replay. See [System checks](FEDERATED_SYSTEM_CHECKS.md). Untouched evaluation is still pending, so the broader requirement remains partial.

Two simulated clients were compared with a centralized model and two local-only models on the existing UCSF development dataset. This is a single-process simulation; clients are artificial case-ID partitions, not hospitals. Sixteen training patients are split eight/eight; four existing development-validation patients are split two/two for per-client reporting. The protected new UCSF cohort is excluded.

Protocol: seed 42, two FedAvg rounds, one local epoch per round, 120×120 slices, batch size 16, Adam 0.001 and gradient clipping 1.0. All arms start from the same initial model; optimizers reset each epoch/round. Centralized and federated total slice draws match. Each local-only model sees half the data. Threshold 0.5 and final checkpoints were fixed before training.

| Arm | Development mean Dice |
|---|---:|
| Centralized | 0.3407 |
| Client A only | 0.2825 |
| Client B only | 0.2200 |
| Federated | 0.4005 |

Per-client metrics, class imbalance, source/checkpoint hashes and all settings are saved in `experiments/federated-simulation-001/`. Reloaded checkpoints reproduced the saved metrics. Resuming round two from round one's saved global state reproduced every final weight exactly. Missing, duplicate, malformed and nonfinite updates fail rather than silently changing participating clients.

These results are one-seed exploratory development evidence, not independent generalization evidence. The manual's untouched-evaluation prerequisite remains unmet; the requirement is partial pending that evaluation and broader recovery/communication validation.

The update API accepts state tensors and sample counts only. The simulation coordinator runs in the same process and can access the data; it is not an enforced privacy boundary. No raw scans or model updates are sent over a network. No authentication between institutions, secure aggregation, differential privacy or poisoning defense is claimed. Finite malicious updates can pass structural checks; model weights can leak information. Real distributed use requires separate validation.

Reproduce in a fresh output directory:

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\benchmark_federated.py --output experiments\federated-simulation-new
```
