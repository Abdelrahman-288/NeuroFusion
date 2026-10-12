# EEG false-alarm reduction — existing 12 recordings

12 October 2026. An operational improvement was achieved, but the excessive
false-alarm problem is **not resolved**. EEG remains partial and unsuitable for
clinical use. No recordings were downloaded or reassigned.

## Conservative policy result

The original six-channel CNN and its 0.5 threshold are retained. A research alarm
now requires two consecutive positive four-second windows. Confirmation starts
at the second window's end; it is never backdated. State resets for each EDF.
There is no refractory period that silently suppresses later alarms.

| Existing validation evidence | Original | Conservative rule |
| --- | ---: | ---: |
| Seizure events matched | 4/4 | 4/4 |
| Timely matches under decision-availability accounting | 4/4 | 4/4 |
| False alarm events | 722 | 591 |
| False alarms per background hour | 72.456 | 59.309 |
| Background seconds in alarm | 31,377 | 28,477 |

The false-alarm count fell **18.14%**. Both validation patients retained their
original matches. Background alarm duration also decreased, but remains about
**79.4% of background time**. This matters: the original 4/4 sensitivity partly
reflects broad, prolonged alarm activity, rather than precise seizure onset
detection. Zero reported latency can mean an alarm was already active before a
seizure; it does not establish instantaneous detection.

This was a fixed conservative follow-up after failed experiments, using already
examined validation recordings. Its protocol artifact explicitly records that
the initial score had already been computed. It is a development result, not
untouched validation or independent clinical confirmation.

## Failed candidates retained

1. A training-only search over six thresholds and four confirmation lengths
   selected threshold 0.95 and four windows. It reduced validation false alarms
   to 484 but preserved only 1/4 original event matches (2/4 under the separately
   defined timely-interval metric). It was rejected.
2. Three fixed retraining seeds used per-window/channel mean removal and RMS
   normalization, and square-root rather than full class-imbalance weighting.
   All used the same eight training recordings, ten epochs, final checkpoints
   and threshold 0.5. Seeds 42/43/44 produced 271/243/334 false alarms, but each
   matched only 1/4 validation seizures. All three were rejected. No favorable
   seed was selectively promoted.

Historical and timely metrics use different interval definitions. Historical
matching retains the original window-support overlap rule. Timely matching uses
when a completed window's decision is available, persisting until the next
window decision. These definitions can produce different matches for short
events. Neither metric alone establishes useful continuous screening.

## Available workflow

`src/neurofusion/eeg_alarms.py` implements causal confirmation, normalization,
event/burden metrics and checkpoint-bound policy application. A failed policy
or mismatched checkpoint is rejected. The conservative policy is stored in
`experiments/eeg-conservative-001/policy.json` and remains research-only.

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\predict_eeg_pilot.py --recording chb01/chb01_01.edf --output experiments/eeg-new-result
```

Use a fresh output directory. This CLI supports only existing prepared pilot
recordings, checks EDF/feature/checkpoint hashes, and does not use seizure
labels for inference. It saves raw probabilities, confirmed windows and
decision times. It does not add EEG uploads to the MRI viewer or enable alerts
for patient care.

## Verification and evidence

- All 12 EDF/feature sources were hash checked; original validation probabilities
  and the 722-event baseline were reproduced.
- All three retrained checkpoints reproduced all 12 validation prediction arrays
  and their metrics on reload.
- Confirmation on all 12 recordings matched an independent causal convolution
  calculation. Tests check record boundaries, no future-window use, delayed
  decisions, short-event misses, normalization and policy/checkpoint rejection.
- **397 repository tests passed**, including 10 focused EEG/specialist tests.

Artifacts: `experiments/eeg-alarm-reduction-001` (rejected rule),
`experiments/eeg-retraining-001` (three rejected candidates and replay),
`experiments/eeg-conservative-001` (policy, case metrics and verification), and
`experiments/eeg-policy-inference-001` (real inference smoke check).

Remaining work is a substantially better sensitivity/false-alarm tradeoff on
the existing data, with reproducible model and policy evidence. The same six
patients and label-selected recordings cannot establish population-level
reliability. No independent-qualification or clinical-ready flag was enabled.
