# Patient and source separation inventory

2026-10-08. All 501 UCSF-PDGM version-5 exam records were grouped into 495
patients using the existing normalized metadata reader. Development identities
were verified against the 20-exam acquired pilot manifest. Source hashes,
per-patient decisions and candidate inventory are in
experiments/pdgm-cohort-separation-001. Reproduce with
scripts/audit_pdgm_cohort_separation.py --help.

| Patient category | Count |
|---|---:|
| All metadata patients | 495 |
| Development pilot patients | 20 |
| Patients with recorded BraTS mappings | 296 |
| Development patients also mapped to BraTS | 13 |
| Conservative remaining candidate pool | 192 |

The candidate calculation is 495 - 20 - 296 + 13 = 192. Reasons are recorded
per patient rather than silently dropping rows. Every exam of a development
patient, including follow-ups, is excluded. A BraTS mapping on any exam also
excludes the whole patient under this planning policy. In the actual metadata,
the development patients have 20 exams total. Synthetic tests cover exclusion
when follow-ups exist and when a mapping appears only on a follow-up.

This is a conservative planning policy, not evidence that the existing BRISC
or ISLES models trained on BraTS. Missing BraTS mappings do not prove source
independence or rule out cross-dataset duplication. The 192 candidates are not
a frozen evaluation cohort, have not been acquired here, and must not be
reported as independent external performance data. No model scoring occurred.

Remaining gates: confirm numeric label semantics and model-target equivalence;
complete anatomical review; investigate patient/source overlap against every
training and development cohort; then choose and freeze a separate compatible
evaluation protocol before inference. The pilot remains development data.

Validation includes unknown/duplicate exam rejection, exactly-one-baseline
requirements, development-follow-up exclusion, follow-up-only mapping exclusion,
and checks that the candidate pool contains neither development patients nor
recorded BraTS IDs. Overall rough platform estimate stays approximately 83%.

Cohort-separation regression: **169 tests passed** in 38.66 seconds, including five new patient identity and follow-up exclusion checks.
