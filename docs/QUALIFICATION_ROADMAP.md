# NeuroFusion: qualification and next milestones

Latest independent-evaluation audit: see `INDEPENDENT_EVALUATION.md`. Local volume similarity and experiment-configuration checks are complete within their stated scope. No qualified reviewer is available; expert review remains 0/20. The UCSF model development gate still fails. Protocol is draft-only, with no independent inference.

Current update (9 October 2026): acquisition is now complete, 20/20 verified pairs; qualification 2/10. See `UCSF_ACQUISITION.md`. The planning snapshot below describes the earlier state.

Updated 8 October 2026. This is a plan for producing reviewable evidence, not a declaration that the model is ready.

## What this stage completed

1. Audited current experimental, dataset, target-contract and expert-review evidence.
2. Defined ten UCSF research-qualification gates with explicit completion criteria.
3. Created a reproducible provisional acquisition queue of 20 new patients.
4. Published a viewer report and corrected progress tracking.

Stage completion: 4/4 deliverables (100%). UCSF qualification: 1/10 gates passed. These denominators describe different things; neither is whole-project completion. The former 86% overall estimate lacked a weighted complete roadmap and is superseded. The new gate count does not mean existing work was lost.

## Evidence and qualification

### Development reproducibility — complete

Required: Hash-pinned checkpoints, source, splits and reproduced predictions.

Current: Completed: 15 new checkpoint hashes and 12 reproduced masks.

### Development performance — failed

Required: All predefined checks pass per seed; explicitly count empty outputs, poor-overlap patients and false-positive volume.

Current: Clipping confirmation failed the false-positive check for seeds 43 and 44.

### Target contract — pending

Required: Freeze supported modality, numeric target union, exclusions and claim wording. Clinical compartment names additionally require version-specific label confirmation.

Current: Numeric foreground engineering target exists; qualification contract is not signed/frozen.

### Cohort independence — pending

Required: Audit patient identities, source mapping, duplicates and all development exposure; document limitations.

Current: 192 metadata candidates are not 192 verified independent patients. Same UCSF source is not external-site validation.

### Acquisition integrity — pending

Required: Acquire approved provisional pairs; verify source/license/version, checksums, geometry, labels and immutable inventory.

Current: 20-patient acquisition queue prepared without labels or model scores; no new files downloaded.

### Expert alignment review — pending

Required: Record whole-volume image/annotation alignment review and exclusions with reviewer identity, date and reason.

Current: Existing pilot expert reviews: 0/20. This cannot be replaced by automated checks.

### Frozen evaluation protocol — pending

Required: Before inference, fix cohort, checkpoint hash, preprocessing, threshold, metrics, confidence intervals, exclusion rules and acceptance criteria.

Current: Do not freeze a model that has not qualified, or select thresholds on this cohort.

### Independent performance — pending

Required: Run the frozen protocol once; report every eligible patient, uncertainty, subgroup limits and all failures.

Current: Repeated use of four development patients is not independent evaluation.

### Application integration — pending

Required: Only after qualification, add a registry entry and test supported volume inputs, original-grid outputs, limits and rollback.

Current: Current viewer still uses BRISC tumor models and the DWI stroke baseline; UCSF remains a research artifact.

### Release review — pending

Required: Review intended research use, data handling, licensing, failure reporting and deployment tests before release.

Current: A research release review does not authorize clinical diagnosis.

## Next executable stage: acquisition and integrity

Use `experiments/ucsf-qualification-001/acquisition-queue.json`. The queue selects 20 baseline examinations from 192 eligible metadata candidates with a deterministic patient-identity hash. It excludes all 20 previously used development patients and recorded BraTS mappings. No patient was selected for a favorable label or model output. Queue size 20 is an initial acquisition batch, not a power calculation or adequate clinical validation sample size.

None of the queued pairs is currently present under the expected project paths. Acquire T1c and supplied numeric tumor segmentation from the official source. Retain source/version/license metadata and original files; hash every file. Quarantine incomplete or invalid pairs. Audit geometry, finite intensities, observed label IDs and duplicate/source overlap. Update acquisition status separately from verification status; file presence does not prove integrity.

Do not train, tune thresholds, inspect model predictions, or select checkpoints using queued cases. A missing recorded overlap does not prove patient independence. Follow-ups must remain grouped with their patient. If a case must be excluded, record the reason and replacement using the remaining deterministic order before model inference. Preserve the selection ledger. The queue is provisional, not frozen.

This would be a held-out cohort from the same UCSF source. It does not establish external-site generalization. Truly external-source/site assessment remains a separate requirement. No new downloads, legal attestations, expert signoffs or model inference occurred in this planning stage.

## Model qualification decisions before evaluation

The clipping candidate did not pass the existing paired-seed performance rules. Keep those failed results unchanged. Before independent evaluation, define a bounded prospective development protocol and an explicit research-use target contract. Select a single checkpoint using development data only, record its hash, and freeze preprocessing and threshold. Numerical acceptance thresholds, sample size and uncertainty reporting must be justified for the intended research endpoint before reviewing held-out results; they are not invented from the four reused validation cases. A human specialist must supply any required expert review, not an automated completion flag.

Numeric annotation-union evaluation can be described literally without asserting that it detects every tumor compartment. Version-specific semantic confirmation is required before adding named compartment claims. A model trained on one modality or label contract cannot silently be presented as covering other brain conditions.

## Other project milestones still open

- Additional planned datasets and specialist branches from the original manual, including CT hemorrhage, angiographic and EEG work, with separate input/label contracts and patient-level evaluations.
- Multi-specialist fusion and uncertainty work; the existing DWI+ADC comparison is an implemented experiment, not proof of a complete fusion platform.
- Qualification of every supported task, independent evaluations and expert review.
- Candidate integration, input-boundary testing, deployment/data-handling review and release documentation.

The local viewer, saved jobs/reviews/reports, existing tumor and DWI baselines, pilot acquisition and engineering experiment tooling are implemented. Do not count those same completed features again every time an experiment finishes. Each new stage should list concrete deliverables and their evidence while readiness remains a separate gate checklist.

## Verification

Queue tests cover deterministic order, patient and BraTS exclusions, duplicate rejection and invalid sizes. Qualification tests reject missing evidence and truthy strings such as "true". The viewer report exposes named report artifacts only, not checkpoints or raw volumes. All 205 regression tests passed; the report and three JSON links passed HTTP checks. Full regression and HTTP verification are recorded in the report's verification.json.
