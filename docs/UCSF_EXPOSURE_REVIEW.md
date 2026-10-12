# Cohort exposure audit and review preparation

9 October 2026. Engineering deliverables: **4/4 complete**. UCSF qualification remains **2/10**; expert alignment review **0/20**. Overall project completion remains unmeasured.

The new evidence snapshot is `experiments/ucsf-exposure-001/`. It contains a hash-inventoried scan, a twenty-patient exposure ledger, a separate pending human-review template, provenance and a local viewer report. The acquisition evidence remains unchanged. Original MRI/annotation copies were rechecked against all 40 acquisition hashes.

The bounded scan covered 1,795 UTF-8 text files in configs, experiments, scripts, src and data. It normalized three/four-digit UCSF patient identifiers and follow-up identifiers, and searched acquisition file hashes. Nine files matched, all in inventory/intake records; none required further classification within this scope. One non-UTF-8 metadata glossary was separately decoded as Windows-1252 and checked: no queued patient identifiers. See `glossary-check.json`.

Raw directories, binary arrays/checkpoints, nonselected file extensions and files over 20 MB are outside the automated text scan. It does not prove absence of unlogged training, renamed data, unknown cross-dataset overlap or near-duplicate content. No new model inference was performed. No independence gate was marked complete. Matching files are references, not evidence of training by themselves.

## Expert review workflow

1. Copy `review-template.json` into a new review submission; preserve the original snapshot.
2. Resolve image/mask paths relative to `experiments/ucsf-exposure-001/` and verify hashes against the acquisition inventory. Open the original volumes in a local NIfTI viewer.
3. Check identities, orientation, geometry and alignment through the entire volume in all three planes, toggling overlays. Sparse screenshots are insufficient. Use supplied numeric IDs; semantic compartment certification remains separate.
4. Record reviewer name, qualification, timezone-aware review date, notes, and accept/exclude/needs_followup. Every accept requires whole-volume review, identity, orientation and alignment checks.
5. Have review submissions checked against source hashes and patient identities before changing any status. `validate_review` validates required fields, not reviewer credentials, judgment, provenance or signature. No submission/import UI or automatic gate promotion is implemented at this stage.

Next work: whole-volume review tooling and source-independence evidence, followed by qualified human review. Keep the cohort provisional and outside training or threshold/model selection. Development performance, model qualification and a prospectively frozen evaluation protocol remain prerequisites to held-out inference.

The viewer exposes only explicitly allowed report files; raw NIfTI files remain unavailable over the research report route. Validation results are in `verification.json`.
