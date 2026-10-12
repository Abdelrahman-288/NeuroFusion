# Development annotation selection

The selection engine in `src/neurofusion/active_learning.py` ranks explicitly eligible unlabeled development patients using normalized uncertainty plus cosine-distance diversity. It produces a deterministic, equal-budget random comparator for a later annotation experiment. It is not clinical triage and does not train a model.

Use `scripts/select_annotations.py --candidates <json> --protected <json> --budget <count> --output <fresh-directory>`. Candidate JSON has `records`; protected JSON has `patient_ids`. Assemble the protected list from every validation, test, external and provisional evaluation manifest before scoring candidates. The engine cannot discover undeclared patient overlap or verify the caller's patient-identity attestations.

Every candidate requires: unique case_id, unique patient_id, partition=train, role=unlabeled_development, patient_identity_verified=true, uncertainty in [0,1], a finite nonzero embedding, embedding_version, uncertainty_method, model_sha256, and input_sha256. Model/method/embedding version must be consistent throughout the pool. Repeated visits must first be grouped into one patient candidate. Protected or ineligible entries reject the whole run rather than silently excluding them. Output preserves provenance and explicitly marks training export forbidden.

## Implemented workflow (2026-10-10)

The selector now feeds authenticated review: select → assign two reviewers → independent masks and effort reports → adjudication → approved export carrying the selection batch and scoring provenance. A three-seed retrospective equal-patient-budget segmentation benchmark has been run on existing development data. A prospective human annotation-time experiment remains pending qualified reviewers.

The prepared `data/active-learning-review-acquisition` contains verified copies of the 16 existing development training patients. It excludes the four development-validation patients and the new protected UCSF cohort. No review accounts or human annotations were generated.

```powershell
cd D:\NeuroFusion
.\scripts\start_active_learning_review.ps1 -Bootstrap
.\scripts\start_active_learning_review.ps1
```

Open http://127.0.0.1:8781/. Bootstrap privately asks for the first administrator password and runs only once. This uses a separate database from the protected cohort's review service.

1. Create two reviewer accounts and one adjudicator account.
2. Under **Active-learning annotation queue**, import `experiments/active-learning-benchmark-002/seed-42/candidates.json`, choose reviewers, and use a budget of four patients. This example is a retrospective development exercise with supplied labels, not a newly unlabeled clinical pool.
3. The server recomputes ranking and assigns cases atomically. It checks its own development partition allowlist, source hashes, patient IDs and protected list. Any ineligible, source-mismatched or already-assigned candidate rejects the import. The protected-cohort service has no selection allowlist and rejects imports.
4. Reviewers inspect MRI volumes, annotate using an external NIfTI editor, upload masks, and report annotation minutes including external-editor work. Effort is self-reported. Reviewers cannot see each other's annotations; supplied dataset masks remain visible as reference.
5. Adjudicators compare completed reviews and resolve disagreements. Approved exports include batch ID, rank, full selection provenance, effort reports, source hashes and final decision. Download selection/review progress to inspect submissions, approvals and effort.

Selection never automatically authorizes training or changes qualification. See [Collaborative review](COLLABORATIVE_REVIEW.md) for account management and limitations. Assignments and submissions remain immutable: use one fresh selection batch per unassigned pool, not multiple benchmark seeds in the same queue.

Candidate import JSON has `records`, `protected_patients`, and optional `seed`. The browser recomputes selection; it does not trust a client-supplied selected-case list. The server adds non-training patients from its configured partition inventory to the protected list. Unknown cross-dataset identities remain outside the guarantees of local IDs.

To recreate the prepared workspace, use `scripts/prepare_active_learning_review.py --output data/active-learning-review-acquisition` with a fresh output directory.

## Retrospective benchmark

Final run 002: mean active-selection Dice **0.2982**, random-selection Dice **0.3354**, paired difference **−0.0373**. Active selection won one of three seeds and did not demonstrate a benefit overall. Saved checkpoint replay reproduced all 24 patient predictions and both arms had equal patient, slice-draw and optimizer-update budgets. No active application model was changed. Full regression suite: **269 passed**.

Report: `experiments/active-learning-benchmark-002/index.html`. Fixed settings: `protocol.json`. Provenance: `provenance.json`. Per-patient results and checkpoints are stored under each seed directory.

- Task: numeric tumor-annotation foreground segmentation from existing UCSF T1c development images.
- Seeds 42, 43, 44 each use four initial patients, twelve candidate patients, four additional selected patients per arm, and eight final training patients.
- A small U-Net is trained from scratch on only the four initial patients. Pool scores use mean binary entropy across all voxels/slices and mean bottleneck embeddings. No candidate mask enters scoring.
- Active selection uses uncertainty plus cosine diversity, weight 0.5. Random selection uses exactly the same pool and patient budget.
- Both final models restart from identical per-seed initialization: Adam 0.001, three epochs, batch size 16, no augmentation, gradient clipping 1.0, final checkpoint, threshold 0.5. All source patients have 155 cached slices, so slice draws and optimizer updates also match.
- Metric: mean per-patient Dice over four development-validation patients on a 120×120 grid. This is not native-volume Dice or independent test performance; these validation patients have been used in earlier experiments.
- Existing labels are revealed retrospectively after selection. Source/cache checksums are checked for integrity but target values are not features. No protected new UCSF image is scored or trained on.

Run 001 is retained for audit but superseded: it weighted a short final image batch like a full batch when averaging entropy. Run 002 corrects this to equal per-slice weighting. Report only run 002.

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\benchmark_active_learning.py --output experiments\active-learning-benchmark-new
.\.venv-neurofusion\Scripts\python.exe scripts\verify_active_learning_benchmark.py --run experiments\active-learning-benchmark-new
```

Verification replays selection, checks equal patient/training budgets, verifies checkpoints and recomputes all 24 arm/patient Dice values. Equal patient count is not equal human effort: a prospective study must compare reviewer-time budgets, adjudication costs and held-out performance using newly completed annotations. The retrospective benchmark does not establish annotation-efficiency or clinical benefit.
