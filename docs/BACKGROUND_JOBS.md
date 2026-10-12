# Background analysis and result history

Implemented 2026-10-06. Open the local viewer at http://127.0.0.1:8766 using
`scripts/launch_viewer.ps1`, as described in `LOCAL_VIEWER.md`.

Submitting a supported input now returns immediately after upload and queue
registration. A single background worker performs inference while the web server
continues serving requests. The page refreshes job status every 2.5 seconds.
It displays queued, running, completed, failed and interrupted states, rather
than an invented numerical inference percentage.

## Using the workflow

1. Select the task and compatible input, then click Analyze locally.
2. Watch the Saved analyses list. You may submit another input while one runs.
3. Close or reload the page if needed. Work continues while the server is running.
4. Click Open result on a completed entry to restore scores, overlays, slice
   controls and downloads without rerunning the models.

The queue accepts at most 10 queued/running jobs together. History shows the
latest 200 records; older records and output files remain on disk. Upload and
result size constraints from the local viewer still apply. There is no automatic
retention cleanup, cancellation, job deletion UI, or storage quota yet.

## Persistence and recovery

`experiments/local-viewer/jobs.sqlite3` stores job IDs, task, basename, status,
timestamps, upload location and failure message. Raw uploads and generated outputs
remain in their existing local folders. Filenames are displayed as text and may
contain private information, so the database belongs with local private artifacts.

On restart, queued jobs resume. Running jobs become interrupted and require a
new submission; partial outputs are preserved but are not served as completed.
Completed and failed records remain unchanged. Earlier result.json outputs are
imported once, without moving their files or rerunning inference. Never run two
viewer servers against the same storage directory. Background execution requires
the laptop and server to remain running; this is not an installed Windows service.

## API and implementation

- POST `/api/analyze?task=...&filename=...`: raw input bytes and the existing
  `X-NeuroFusion-Request: 1` header; HTTP 202 with `{job: {...}}`.
- GET `/api/jobs`: `{jobs: [...]}`, newest first, up to 200 entries.
- GET `/api/jobs/<id>`: one status record, or HTTP 404.
- GET `/results/<id>/<filename>`: available only for a completed job.
- GET `/api/health`: reports viewer protocol version 2.

The POST response replaces the previous synchronous `{job, result}` response.
Clients must poll status, then fetch the completed result JSON. Model result
schema version 1 is unchanged. The backend uses SQLite transactions to bound
admission and claim queued work, and closes each database connection after use.
The worker and persistence code is in `src/neurofusion/jobs.py`.

## Validation and remaining work

65 automated tests pass across the project (62 existing/queue tests plus 3 HTTP
handler tests). Tests cover persistence, restart interruption, queue resumption,
legacy import, capacity limits, submission during active work, recovery after
inference failure, HTTP 202/status/result behavior, and access restrictions.
Browser validation submitted a real development MRI image, observed running and
completed states, reloaded the page and reopened its saved predictions.

This milestone adds workflow features, not new model training or clinical
validation. Next: human review notes and annotations with a clear distinction
between model predictions and reviewer observations. Authentication, public
deployment, calibration, external evaluation and more specialists remain pending.
