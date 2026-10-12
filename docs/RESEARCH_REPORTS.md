# Downloadable research reports

**11 October 2026 update:** New results include validated predicted-region measurements and finding-to-preview links. DWI provides physical volumes from verified millimeter geometry; tumor images retain pixel-only measurements. Report export verifies file hashes, coordinates and overlay content. See [Measurements and evidence](MEASUREMENTS_AND_EVIDENCE.md). The original milestone description below describes older result fields.

Implemented 2026-10-06. Open a completed analysis in the local viewer. Under Model
outputs, use Open research report, Download offline report (HTML), or Download
report snapshot (JSON). HTML files contain embedded preview images and work
without the running server. The browser print command can print the report or
save it as PDF; there is no direct PDF-generation endpoint in this milestone.

## Contents

- Analysis ID, recorded filename and timestamp, input SHA-256, inference device,
  checkpoint hashes and the SHA-256 of the saved result JSON.
- Uncalibrated class scores when available, prediction threshold and predicted
  pixel/voxel count. Counts are not physical volumes or severity scores.
- Saved model limitations, without generated medical interpretation.
- Side-by-side input and prediction previews: the default view plus each distinct
  slice linked from a matching review entry. For DWI the default view is the slice
  with the largest predicted mask area, not a clinician-selected representative
  slice. Other slices remain available in the interactive viewer.
- Separately labeled reviewer observations, assessment, timestamp, slice number,
  entry ID and reviewed-result hash. A hash mismatch is highlighted and that
  entry does not select a preview image for the current report.

Earlier imported results have a record timestamp derived from the result file's
modification time, rather than a known original submission time.

## Snapshot behavior and scope

Each export captures the current saved result and review list. Later notes do not
change a downloaded file; download again for an updated snapshot. HTML contains
selected PNG previews; JSON contains the full saved result metadata and review
entries, but does not embed image bytes. Neither export includes raw scans, full
probability arrays or weights. Use the existing probability download separately.

Reports may contain private filenames, images, reviewer labels and notes. They
are research records, not clinical reports. Reviewer identities remain unverified.
HTML escapes user-controlled text, allows only embedded PNG assets and inline
styles through its content-security policy, and contains no scripts. Preview
paths are restricted to the completed result directory. No external service,
LLM, network upload or extra dependency is used to generate reports.

## Implementation and API

`src/neurofusion/reports.py` builds the version-1 snapshot and renders HTML.
GET `/api/reports/<job>` previews HTML. Add `?download=1` for an attachment,
or `?format=json&download=1` for JSON. Only completed jobs can be exported;
Host checks apply. Viewer health protocol version is now 4. Missing or invalid
assets produce an explicit error rather than a silently incomplete HTML report.

## Verification

85 automated tests pass. New tests cover escaping, embedded images, no mutation
of prediction files, snapshots unaffected by later review entries, hash mismatch
warnings, asset-path containment, completed-job gating and JSON HTTP behavior.
Browser testing confirmed the HTML download and displayed a real development DWI
report with its saved Development QA annotation. Both DWI and tumor examples
are saved under `experiments/report-verification-001`.

The browser layout was inspected; automated PDF pagination and direct PDF export
are not implemented or verified. Authenticated sharing, collaborative review,
clinical validation, additional specialists and grounded external explanations
remain pending. Next milestone: input-quality checks and explicit compatibility
warnings before inference, with measurable tests rather than clinical claims.
