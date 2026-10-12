# Human review notes and slice annotations

Implemented 2026-10-06. Open a completed result in the local viewer and scroll
to Human review. Enter a reviewer label, choose Uncertain, Needs attention or
Reviewed, and write an observation. Optionally attach the note to the displayed
image or DWI slice, then select Save review entry.

Saved notes appear below the form. Show image / slice returns to the referenced
view; Download review history JSON exports the entries for that analysis.
Reviewed means a person recorded a review, not that a model is correct or that
a scan is healthy. Reviewer labels are self-entered and not authenticated.

## What is stored

Each entry is a separate row in the reviews table in
`experiments/local-viewer/jobs.sqlite3`. It includes a random entry ID, job ID,
UTC timestamp, reviewer label, assessment, note, optional zero-based view index
and SHA-256 of the exact result.json at review time. DWI view indices refer to the
canonical RAS preview order, not native scanner slice numbering. The interface
shows one-based image/slice numbers. Notes do not change model predictions,
probability arrays, masks, checkpoints or training labels.

The application only appends entries. To correct an observation, save a new note
explaining the correction; earlier entries remain. This is a local record, not a
tamper-proof audit system. A user with filesystem access can modify the database.
The hash ties an entry to its saved result JSON, not to every generated asset.

Reviewer labels allow 1–80 characters, notes 1–4000 characters. Assessments and
view bounds are checked by the backend. Reviews require a completed job. The
browser renders notes as text. Both review API routes retain the existing Host
checks; writes also require the same-origin rule and custom request header.

Drafts are retained in memory when switching between results on the current
page. Navigating away with a nonempty unsaved note triggers the browser's unsaved
changes prompt. Drafts are not persisted across reloads; save before leaving.
Saved notes survive page reloads and server restarts. Exported JSON contains
review text and reviewer labels and should be treated as local private data.

## API

- GET `/api/reviews/<job>` returns version-1 JSON with job ID, research-only and
  unverified-identity flags, and an ordered list of saved entries.
- POST `/api/reviews/<job>` accepts a JSON object containing `reviewer`, `note`,
  `assessment` (`reviewed`, `needs_attention`, `uncertain`) and `slice_index`
  (null for a whole-analysis note). It returns HTTP 201 with the saved entry.
- Maximum request size is 20,000 bytes; the viewer health version is now 3.

## Verification and limits

79 automated tests pass. Added tests check persistence, append-only behavior,
unchanged prediction files, job isolation, completed-job requirements, input and
slice validation, and the HTTP authorization/roundtrip behavior. Browser testing
saved an explicitly labeled Development QA note on the existing development DWI
result, reloaded it, and returned to slice 20 using the saved annotation link.
The test note is retained and clearly states that it is not a clinical finding.

This stage supports text annotations linked to images/slices. It does not include
bounding boxes, freehand mask editing, verified identities, user roles, multi-user
collaboration, expert adjudication or automatic learning from feedback.

Next milestone: a downloadable research report combining model provenance,
outputs, limitations and separately labeled reviewer observations. External model
evaluation and additional brain-condition specialists remain on the roadmap.
