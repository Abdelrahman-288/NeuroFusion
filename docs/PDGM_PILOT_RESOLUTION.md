# Full pilot resolution audit

2026-10-08. All 20 acquired development-pilot exams were audited at 128, 240 and
256 pixels (60 case/resolution comparisons). No model inference was performed.
Source hashes were checked against the immutable import-004 manifest. Protocol,
per-case results, source snapshots/hashes, header checks and a technical review
queue are saved in experiments/pdgm-pilot-resolution-001.

| Size | Exams losing component overlap | Components without overlap | Slices losing numeric IDs |
|---|---:|---:|---:|
| 128 | 14/20 | 267 | 19 |
| 240 | 0/20 | 0 | 0 |
| 256 | 0/20 | 0 | 0 |

At 128, mean case roundtrip Dice for numeric labels 1, 2 and 4 was 0.8967,
0.9210 and 0.8728 respectively. Contributions are 17, 20 and 18 exams: absent
labels are omitted rather than counted as perfect matches. Minimum case Dice
was 0.6667, 0.8066 and 0.6186 respectively. These are annotation sampling
measurements, not model performance. Both higher-size categorical roundtrips
were exact for every present label in the pilot.

Components use 26-connectivity independently per ID. A component is counted
when no reconstructed voxel of the same ID overlaps it. Counts do not establish
separate lesions and do not fully quantify partial loss, merging or boundary
changes. Reconstruction uses nearest-neighbor categorical labels; future model
probability reconstruction is a separate operation. Exact categorical roundtrip
does not establish lossless intensity resampling or safe model input changes.

All 40 source-file spatial headers were checked; no coded qform/sform conflicts
were found. This is not expert confirmation of anatomical alignment. Review
entries remain pending; numeric label semantics are also unverified.

Decision: retain original masks as scoring truth. Keep model inputs/checkpoints
unchanged. Resolve semantic target mapping and alignment review, establish
patient/source independence, then freeze an evaluation protocol before scoring.
The pilot was used for development and is not an untouched evaluation cohort.

Validation: 155 tests passed in 55.33 seconds, including three new rejection
checks for changed source hashes, dataset-root escape and incomplete imports.
The previous adapter/resolution tests also passed (13 focused tests). Cohort
completion was verified and aggregate component counts cross-checked against
all per-case reports. Overall platform estimate remains ~83%; this QA stage and
pilot acquisition are complete, while external evaluation remains pending.
