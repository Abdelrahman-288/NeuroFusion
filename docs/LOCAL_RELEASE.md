> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

# Local research preview packaging and recovery

This package is a research preview, not a declaration that the full project is complete. It packages source code, static web assets, configuration, tests, instructions and the three existing hash-pinned application checkpoints. Scans, uploads, review accounts, sessions, annotations and experiment result directories are excluded. There is no automatic model promotion.

Build and verify:

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\package_local_release.py --output experiments\local-release-preview-001.zip
.\.venv-neurofusion\Scripts\python.exe scripts\package_local_release.py --verify experiments\local-release-preview-001.zip
```

Recovery always targets a fresh directory; it refuses to replace an existing installation:

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\package_local_release.py --restore experiments\local-release-preview-001.zip --destination experiments\local-release-restore-001
```

Every archive member is listed by hash and size in `bundle-manifest.json`. Verification rejects corrupt content, duplicate names, undeclared members, traversal paths, Windows device names and symbolic links. Restore validates the complete archive before writing. A checksum verifies consistency, not publisher identity; the manifest is not digitally signed.

The Python/CUDA environment is not embedded. Follow the environment instructions in the packaged README, then install the package and dependencies. Existing application models are included; datasets and research/review reports must be supplied separately. The viewer should run on loopback only. The review service requires its own source acquisition manifest and local account bootstrap.

For rollback, retain the earlier package and restore it to a separate directory. Do not overwrite running code or private databases. Private review and result backups require stopping their writers and separately copying the complete storage directory plus its source manifests/volumes to protected storage. This code package is not a private-data backup.

## Release verification, 12 October 2026

The deployment target is the existing single-user, loopback-only Windows research viewer. Public/network hosting has not been verified or enabled. Clean-machine verification remains outstanding; the same-laptop checks below do not establish it.

- `experiments/local-release-preview-002.zip`: 379 hash-checked files, restored to `experiments/local-release-restore-002`. This immutable snapshot precedes this documentation update.
- `experiments/local-wheelhouse-002/neurofusion-0.1.0-py3-none-any.whl`: built offline from the restored source using the already installed Codex runtime's setuptools/wheel. The project environment initially failed wheel building because `bdist_wheel` was absent. No dependency downloads or changes to the working environment were made.
- Installed the wheel with `--no-index --no-deps --target experiments/local-installed-002`. `experiments/local-install-verification-002.json` proves imports came from that installation, all three pinned models loaded on CPU, the viewer and health routes returned 200, and source/checkpoint URLs returned 404. A temporary loopback server was shut down after the checks. Existing host dependencies were reused; GPU inference was not retested here.
- `pip check` passed in the working environment. The 25 focused backup, monitoring, archive and HTTP tests passed.
- `experiments/private-viewer-backup-001.zip`: 173 private files, restored to `experiments/private-viewer-recovery-001`; hashes and both database integrity checks passed. Restored counts: five jobs, one job review and zero cohort reviews. No live writer was running during the drill. This covers the local viewer storage, not source datasets or unrelated experiment directories. No separate collaborative account database was found in the experiment inventory; real account recovery is therefore not claimed.
- `experiments/local-monitor-001.json`: disk space, pinned models, database integrity and all four completed results passed. Monitoring deliberately reports unhealthy because one historical failed job exists: an input was rejected for no grayscale intensity variation. This is an input-validation rejection, not a failed model load. The job history remains unchanged.

## Private-state backup and recovery procedure

Stop writers normally before taking a backup. The tool refuses SQLite journals and checks that the file inventory/hashes did not change during the snapshot; it does not stop services or provide a transactional snapshot of running writers. Choose new filenames/directories each time.

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\release_operations.py backup --source experiments\local-viewer --archive experiments\private-backup-NEXT.zip
.\.venv-neurofusion\Scripts\python.exe scripts\release_operations.py restore --archive experiments\private-backup-NEXT.zip --destination experiments\private-recovery-NEXT
```

Recovery refuses an existing destination. Check the restored databases and results before a manual cutover, retaining the old installation. Pending uploads may contain absolute source paths in the job database: do not resume pending jobs after relocating storage; resubmit those inputs. This drill had no queued/running jobs. Do not copy a recovery over a live database.

The private archive is **unencrypted and on the same disk**. Protect access as carefully as the source data. It verifies application recovery, not protection against disk failure. An encrypted off-device backup and its recovery test remain unverified; no external copy was made.

## Monitoring and deployment runbook

```powershell
.\.venv-neurofusion\Scripts\python.exe scripts\release_operations.py monitor --output experiments\local-monitor-NEXT.json
```

Exit 0 means the checked conditions passed; exit 2 means at least one check failed. Inspect `checks` and `details`: check failed/interrupted job messages, preserve evidence, correct the cause and resubmit supported input as needed. Restore a damaged checkpoint from a verified release rather than changing its expected hash. Stop writers and use verified recovery if a database integrity check fails. Free disk space without deleting required source evidence. Historical failures continue to flag until deliberately dealt with; this tool never deletes or rewrites them.

Monitoring is a one-shot operator check, not a background monitor or notification service. Run it before/after a local session; retain the JSON output. The `/api/health` endpoint is only HTTP liveness, not model quality or dependency health. No scheduled task was installed.

For offline installation, use the verified wheel with the existing compatible Python environment:

```powershell
.\.venv-neurofusion\Scripts\python.exe -m pip install --no-index --no-deps --target experiments\local-installed-NEXT experiments\local-wheelhouse-002\neurofusion-0.1.0-py3-none-any.whl
```

The wheel contains the Python package; retain the restored release directory for viewer assets, scripts and checkpoints. Run the viewer with an environment that imports the installed package, from that restored directory. Clean-machine installation still requires all compatible dependencies to be available locally. The release remains partial until that separate environment is actually tested. These checks do not close independent model qualification or establish clinical readiness.

Verified on this laptop: `experiments/local-release-preview-001.zip` contains 306 hash-checked files, restores into a fresh directory, and all three packaged model checkpoints load through the restored source code. The existing Python environment was used; this is not a clean-machine installation test. The archive is an immutable preview snapshot; later documentation changes are not automatically included.
