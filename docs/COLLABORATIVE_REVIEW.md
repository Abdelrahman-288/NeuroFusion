# Collaborative review

Implemented 2026-10-10 as a separate **local** research service. Five software capabilities are implemented: accounts, reviewer assignments, independent mask submissions, adjudication and approved label export. Actual expert review remains 0/20; this implementation creates no human reviews or clinical qualification.

## Start on Windows

Run these commands in PowerShell. Bootstrap prompts privately for a password; there are no default accounts or passwords.

```powershell
cd D:\NeuroFusion
.\.venv-neurofusion\Scripts\python.exe scripts\serve_collaboration.py --bootstrap
.\.venv-neurofusion\Scripts\python.exe scripts\serve_collaboration.py
```

Open http://127.0.0.1:8780/. Keep the terminal running. The existing model viewer on port 8766 remains separate. Subsequent starts need only the last command. Bootstrap works once per storage directory.

Default source: `experiments/ucsf-acquisition-001/summary.json`. State: `data/collaborative-review/`. Alternate versioned cohorts may be selected with `--acquisition` and a new `--storage`. Do not use a new storage directory to hide or replace prior reviews.

## Workflow

1. Administrator signs in and creates two reviewer accounts and a separate adjudicator account. Supply account credentials privately outside the app. Administrators can deactivate accounts and reset passwords, immediately revoking their sessions. Roles are fixed after creation.
2. Administrator opens a case and assigns two distinct active reviewers. Assignments lock immediately. This version does not support reassignment or revisions; resolve account mistakes before assigning. A future correction workflow must retain the original audit trail.
3. Each reviewer signs in separately. Only assigned cases and their own annotations are visible. Review the entire MRI in sagittal, coronal and axial planes. Acknowledging whole-volume review is a human attestation, not automatic verification that every slice was inspected.
4. Download the original MRI. Create or correct a mask in an external NIfTI annotation editor. The browser supports inspection and upload, **not voxel painting**. A supplied dataset mask can be viewed as a reference; independence here means reviewers cannot see each other's submissions, not that they are blinded to the supplied dataset annotation.
5. Upload the original-grid `.nii` or `.nii.gz` mask: matching shape, affine and spatial units; only numeric labels 0, 1, 2, 4. These are preserved dataset label IDs, not inferred diagnoses. Upload limit 25 MiB, expanded limit 80 MiB. Geometry is checked without resampling. An accepted review requires a mask; exclusion or follow-up reviews contain no mask. Add rationale and explicitly confirm final submission.
6. Once both submissions are complete, the adjudicator can inspect both reviewer masks across the same MRI slices, download them and read both rationales. Different decisions or normalized mask hashes flag a disagreement. Choose one accepted mask with a resolution rationale, or exclude the case. This version resolves disagreements by choosing an existing submitted mask or excluding; it does not merge masks or reopen editing rounds.
7. Administrator or adjudicator exports approved cases. No incomplete, follow-up-only or excluded case can enter an approved export. ZIP includes `labels/<exam>.nii` plus a versioned `manifest.json` with source hashes, both reviewer IDs and submissions, final adjudicator decision, selected mask hash, timestamps and export ID. The full ZIP has a recorded SHA-256 checksum. Export does **not** authorize training on a protected evaluation cohort.

## Permissions and persistence

| Role | Capabilities |
|---|---|
| Administrator | Accounts, assignments, queue counts, approved exports, audit log; no unapproved reviewer masks |
| Reviewer | Assigned source scans, own immutable submissions; no other reviewer masks or notes |
| Adjudicator | Source scans; both annotations only after two submissions; immutable resolution and approved exports |

Passwords use salted scrypt. Random bearer sessions expire after eight hours; only token hashes are stored. The browser holds tokens in memory, so a page reload requires sign-in. Five failed logins lock that username for five minutes. Administrator password reset clears the lock. There is no email/password recovery service.

The service binds only to `127.0.0.1`, rejects unexpected Host/Origin and cross-site requests, uses no authentication cookies, and sends no CORS permission. CSP restricts scripts to local assets. Do not expose it through a tunnel, reverse proxy or public host. Remote collaboration, TLS, MFA, professional identity verification and production security review remain separate deployment work.

Database transactions prevent double submission. Source inventory and scan hashes are rechecked before reading, submitting, adjudicating and exporting. Saved masks and exports are rehashed before use. Application-level immutable records and audit events do not make files tamperproof against the Windows account owner. Protect the storage directory with OS permissions and back it up together with the source inventory and volumes while the service is stopped. There is no browser deletion operation or automated retention policy.

No access to model inference, training, qualification promotion or the protected cohort's release gates is added by this service. Existing anonymous workbench observations are not imported as authenticated expert reviews.

## Verification

`tests/test_collaborative_review.py` exercises authorization, blinding, source/mask validation, immutable review/adjudication, disagreement selection, export integrity, exclusion, password/session lifecycle and HTTP origin/host boundaries using temporary synthetic scans and accounts. Synthetic test reviews never populate the real cohort.

```powershell
.\.venv-neurofusion\Scripts\python.exe -m pytest tests/test_collaborative_review.py -q
```

Implementation: `src/neurofusion/collaborative_review.py`, `scripts/serve_collaboration.py`, `web/collaboration/`.

Security references: [Python scrypt](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt), [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html). These inform implementation; they are not certification.
