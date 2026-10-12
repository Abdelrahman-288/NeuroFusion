# Data independence: completed identity and overlap disposition

Completed 10 October 2026 under the user's requirement to **resolve or document**
uncertain patient identities and possible overlap, using existing data only.
The audit/documentation task is complete. **Global patient independence is not
certified**, and the independent-evaluation qualification gate is not passed.

## Verified scope

| Collection | Checked | Result and allowed interpretation |
| --- | --- | --- |
| BRISC | 6,000 image assignments; recorded group, byte and pixel hashes; 1,352 recorded similarity edges | No active partition conflicts. 534 images remain quarantined. These are image-similarity groups, not verified patients. |
| ISLES | 248 retained subject assignments; recorded image hashes; quarantine exclusions | 174 train / 37 validation / 37 holdout. Subjects 0090 and 0169 remain excluded. No recorded cross-partition hash conflicts. This is an internal subject split, not external-site validation. |
| UCSF | 40 exam-to-patient mappings against local publisher metadata; patient roles; 80 source-file hashes | 20 development and 20 protected patients have no identity-role conflict. Known BraTS mappings are listed in the audit; none belongs to the protected set. |
| CHB-MIT | 12 recording checksums and canonical patient roles | Six patients, four train and two validation; no role conflicts. `chb21` is an alias of `chb01`, not a new patient, and is absent from this pilot. |

BRISC and ISLES comparisons use the existing frozen manifest fingerprints;
their source pixels were not rescanned in this task. UCSF and EEG source files
were rehashed. The prior UCSF 590-comparison canonical-thumbnail screen is
retained as historical evidence: no exact-volume or near-similarity flags at
its stated threshold. Its images were not newly fingerprinted in this task.
Recorded byte hashes were also compared across the four collections, with no
cross-collection byte-identical file matches. Different modalities, compression
or crops can conceal shared subjects; this is not a cross-source patient test.

## Issue register and disposition

| Issue | Disposition | Consequence |
| --- | --- | --- |
| BRISC patient IDs unavailable | Documented as unresolvable from current local metadata | No patient-independent BRISC performance claim; never derive patient IDs from image names. |
| No common patient identifier between collections | Documented unknown | Do not fuse records across datasets as the same patient or call them independent merely because dataset names differ. |
| Cropped, transformed or unrecorded duplicates | Documented coverage limit | Negative exact-hash and thumbnail checks do not clear all possible overlap. |
| UCSF/BraTS mappings | Resolved where the publisher provides a mapping; explicit list preserved | Treat matching mapped IDs as related data. No mapping is not proof of independence. |
| Two duplicate-content ISLES subjects | Resolved by existing quarantine | Exclusions remain in force; no subjects restored or split assignments changed. |
| EEG subject alias | Resolved in canonical grouping | Keep all recordings from aliases in one patient group. |
| Repeated validation use | Documented known exposure | Existing development and calibration results are not untouched evaluation. |
| Unlogged historical exposure | Documented unknown | Cannot certify absence of all past training or inspection from logs alone. |

Every issue has a machine-readable status, finding and disposition in
`experiments/data-independence-closure-001/issue-register.json`. Unknowns are
documented limitations, not successfully resolved identities. No new evidence
was invented and no external information or datasets were downloaded.

## Permitted conclusions and remaining boundaries

- Existing within-dataset role and duplicate checks can be reported with their
  exact scope. Preserve all current quarantines and protected partitions.
- UCSF's protected cohort is same-source, not a different-site validation set.
- The current task is complete because all reviewed uncertainties have explicit
  dispositions. The separate model-independent-evaluation requirement remains
  open and must honestly describe unknown provenance and prior exposure.
- No qualification evidence flag such as `independence_verified` is set to true.
- No scans were used for inference, no labels changed, and no data moved between
  partitions during this audit.

Evidence: `summary.json` contains collection counts and checks; `evidence-hashes.json`
binds the source metadata and prior audit artifacts. The verification script
checks the saved dispositions and source bindings without invoking models.
