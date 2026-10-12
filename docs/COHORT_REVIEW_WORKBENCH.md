# Full-volume cohort review workbench

Open `http://127.0.0.1:8766/cohort-review` with the local viewer running. It covers all 20 acquired provisional UCSF cases. Every slice is accessible along all three canonical RAS axes, with numeric annotation overlays, direct slice-index entry, previous/next buttons, physical axis coordinates and physical display aspect ratio.

The image uses a fixed whole-volume nonzero p1/p99 display window. It is an 8-bit review rendering, not a quantitative intensity measurement or a replacement for diagnostic imaging software. The original image and supplied mask stay unchanged. Conflicting qform/sform geometry, oblique grids, changed source checksums and invalid slice requests are rejected. A two-volume cache bounds resident arrays; source hashes are rechecked before serving cached views.

The review form records self-entered reviewer identity/qualification, decision, timestamp, rationale, explicit checks, source hashes and acquisition-manifest hash. SQLite history is append-only at the application level, stored in `experiments/local-viewer/cohort-review/reviews.sqlite3`. Revision checks reject stale concurrent submissions. This is not authenticated multi-user collaboration or a tamper-proof archive. Export history as JSON from the workbench.

Accept requires assertions of whole-volume, identity, orientation and alignment review. These assertions are not automated evidence that the user inspected every voxel, or that the reviewer is qualified. No review automatically changes training eligibility, cohort independence or qualification gates. No real expert submissions were generated during implementation; automated POST tests used synthetic volumes and temporary databases.

Verification: `experiments/review-workbench-001/` contains actual-cohort HTTP checks for 20 cases and 120 boundary slices. Unit/integration tests cover all orientations, overlay differences, invalid requests, source mutation, repeated revisions, concurrent-edit conflicts and same-origin POST restrictions. Browser controls were tested for last-slice navigation and annotation toggle.
