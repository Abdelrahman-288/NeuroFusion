# Independent evaluation: current handoff

Identity/overlap disposition update (10 October 2026): [data independence audit](DATA_INDEPENDENCE.md) completes the user's “resolve or document” task across all four retained datasets. Remaining unknowns are explicit limitations; this does not certify patient independence, freeze the evaluation protocol or qualify a model.

Updated 10 October 2026. **Independent evaluation is not complete.** The user explicitly removed mandatory expert review from the completion scope. It no longer blocks protocol freeze or research release. Review tools remain optional; no expert judgments, signatures or qualifications are claimed. Historical snapshots retain their original criteria; current qualification is recorded in `docs/research_qualification.json`.

## Completed automated checks

`experiments/independent-evaluation-001/` preserves a new audit snapshot:

- 80 original image/mask files verified against existing acquisition/development hashes.
- 20 provisional UCSF cases compared with 20 recorded development cases.
- 590 image comparisons: 400 between cohorts and 190 within the provisional cohort.
- No exact canonical voxel duplicates or near-similarity flags at the predefined 0.995 threshold.
- No known patient identity overlap or recorded BraTS mapping among the proposed patients.
- 43 experiment configuration files checked: no proposed-patient identifier references found.
- Current review database checked read-only: no submissions.

The similarity screen uses canonical RAS intensity thumbnails with standardized nonzero intensities. It can detect some intensity-scaled copies; it does not perform registration, crop searches or comparison against unavailable datasets. No flags is not proof of independence. Shared anatomy can also produce false-positive flags. The protocol, all pair scores and source inventory are saved, so the scope is inspectable. No cohort exclusions or selections changed as a consequence of scores.

## What must happen before freezing or testing

1. **UCSF model qualification:** select a compatible UCSF specialist that passes its development checks. The BRISC segmentation confirmation concerns a different model/data contract; the stroke model requires DWI and cannot be tested on these T1c tumor pairs.
2. **Source-exposure resolution:** review development provenance and unresolved cross-source identities. Document the audit scope and unresolved exclusions. The current UCSF cohort is same-source, not external-site validation.
3. **Data-quality and exclusion record:** preserve automated integrity, geometry, label and identity checks and document exclusions before evaluation. Human review is optional. Automated checks do not establish expert-confirmed annotation correctness.
4. **Protocol decisions:** finalize the supported numeric target, one checkpoint hash, preprocessing, threshold, eligible cohort, exclusions, statistical plan and justified acceptance criteria before inference. A 20-patient convenience batch is not a justified clinical sample size.
5. **Freeze and execute:** bind approved evidence and all sources by hash, lock the cohort and configuration, and run once. Report every included case, exclusions, uncertainty and failures. Do not tune against this cohort after inspection of predictions.

The historical saved `evaluation-protocol-draft.json` has no candidate checkpoint, threshold or invented acceptance values. It remains **DRAFT_NOT_FROZEN**. No independent inference has been performed. Current qualification is 2/9 required UCSF gates after removing the expert-review gate; no other gate was waived. The audit builder now omits mandatory expert review from newly generated protocols.

## Reviewer handoff

Open `http://127.0.0.1:8766/cohort-review`. The existing workbench provides all slices in three planes, overlays, source hashes, decision fields and append-only application review history. Review instructions and limitations are in `docs/COHORT_REVIEW_WORKBENCH.md`. The original separate submission template remains `experiments/ucsf-exposure-001/review-template.json`.

Reviewer checklist: verify the source/exam identity; inspect the full image and overlay in all planes; check orientation and alignment; document discrepancies; choose a justified decision; record name, relevant qualification and timezone-aware date. Do not accept a case solely because automated geometry or similarity checks passed. Preserve exclusions and reasons before inference. Do not use predictions to decide which cases to retain.

Report: `http://127.0.0.1:8766/research/independent/index.html`.
