# NeuroFusion local research application — final delivery

## Completion definition accepted on 12 October 2026

The user accepted finishing the research application without guaranteeing that
every model meets its performance requirements. Completion now means working,
tested local software; reproducible research outputs; explicit failed/blocked
experiment outcomes; and restrictions that preserve scientific integrity.
It does not mean all models qualified. No scientific gate was lowered.

The authoritative machine-readable acceptance is `research_delivery.json`,
generated only after the final regression, installation, recovery, candidate
rejection and evaluation-disposition checks pass. `release_status.json` and
the local `/release-status` page show delivery completion separately from the
original quality statuses. The scope retains 19 groups; no datasets or new
features were added. Historical reports and the original PDF remain historical.

## Delivered application

- Local browser viewer: supported tumor images and DWI volumes, background jobs,
  history, masks, source-linked findings, measurements, reports and review notes.
- Data pipelines and existing BRISC, ISLES, UCSF and 12-recording EEG experiments.
- Collaboration, adjudication, approved annotation exports and active learning.
- Versioned annotation-to-training-to-evaluation pipeline, strict candidate
  acceptance and reversible model registry. Failed candidates stay inactive.
- Fusion, uncertainty, robustness and federated experiment tools with recorded
  results and limitations, rather than unsupported claims of improvement.
- Offline release package, installed-package smoke checks, private local backup
  recovery and an operator monitoring command.

## Run the delivered application

```powershell
Set-Location D:\NeuroFusion
.\.venv-neurofusion\Scripts\python.exe scripts\serve_viewer.py --port 8766
```

Open **http://127.0.0.1:8766/**. If NeuroFusion already runs on that port, use that
instance. Upload only the modality and format described by the chosen analysis.
Open **http://127.0.0.1:8766/release-status** for the current delivery and quality
status. The application is a local research prototype, not a diagnostic service.

## Closed with documented limitations

| Area | Final disposition |
|---|---|
| Tumor | Existing pinned models retained; improved-model checks and uncertainty results recorded. Patient independence and screening specificity not established. |
| Stroke | Baseline retained; changes that introduce new misses rejected. |
| UCSF | Specialist remains experimental because improvements were inconsistent. |
| Fusion | DWI baseline remains default; weaker fusion candidates restricted and ADC-only inference disabled. |
| Uncertainty | Conservative abstention remains; useful independently qualified coverage is not established. |
| EEG | Development false alarms reduced to 591, still excessive; not deployed as a clinical seizure alert. |
| Federated | Local recovery, serialization and development comparison verified; no real-network privacy claim. |
| Final evaluation | Targets and eligibility audit recorded. Zero eligible models; protocol remains blocked and protected evaluation was not run. This is an explicit research outcome, not a passed evaluation. |
| Promotion | Real versioned candidate rejected. Synthetic acceptance/rollback tests verify controls without changing production models. |
| Release operations | Same-laptop installation and same-disk recovery verified. Clean-machine installation, encrypted off-device recovery and public deployment are not part of this delivered local environment and remain unverified. |

These limitations are not a promise of future work within this completed delivery.
Further model improvement or broader deployment is a separate project decision.
Expert review remains optional; no approvals or reviews were fabricated.

## Verification and maintenance

See `MODEL_PROMOTION.md` for the completed training integration and
`LOCAL_RELEASE.md` for the backup, monitoring, recovery and installation runbook.
The full regression result is `experiments/research-release-tests-001.xml`.
`research_delivery.json` binds the verified code, tests and evidence by SHA-256;
changes invalidate that specific acceptance until checks are rerun. Hashes are
integrity evidence, not digital signatures or medical certification.

The research package excludes patient scans, uploads, account databases and
private experiment results. Keep private backups protected; the existing local
backup is unencrypted. No public upload, deployment or data download occurred.
