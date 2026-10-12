# Original-grid alignment review gallery

2026-10-08. Gallery: experiments/pdgm-alignment-gallery-001/index.html.
Generator: scripts/build_pdgm_alignment_gallery.py (see --help).

Twenty pilot exams have nine label-independent views each: 25%, 50% and 75%
along each canonical RAS voxel axis, rounded to the nearest index. The gallery
contains 180 views and 360 PNG files, with MRI and transparent numeric-mask
layers separated so overlays can be hidden. The display uses nonzero-volume
p1/p99 windowing, records slice indices and spatial transforms, and preserves
original slice pixel dimensions. CSS maintains physical aspect ratio. It does
not use the lossy 128-pixel training masks. Oblique grids are rejected rather
than incorrectly labeled as anatomical planes.

Source hashes, permitted numeric labels and image/mask geometry are checked.
All 360 PNG files decoded successfully; all 360 browser images loaded. The
hide/show mask control was checked in both states, and the browser preview was
visually inspected. Evidence: summary.json, verification.json and browser-preview.png
in the gallery folder. Generator source and its hash are archived there.

All 20 alignment reviews remain pending: these nine sampled views can miss
problems elsewhere. This is a technical review aid, not an expert review or
clinical approval. It provides no edit or approval form. No trained model,
checkpoint, inference behavior or evaluation status changed. Last full model/
pipeline regression remains 164 passed; this standalone gallery was verified
through actual generation, file decoding and browser behavior.

Open index.html directly for offline use. A temporary loopback preview is also
available on http://127.0.0.1:8771/ while its server is running.

Next: review full-volume alignment, confirm version-specific label mapping and
model target equivalence, then define a separate independent evaluation protocol.
Overall implementation estimate remains approximately 83%; gallery generation
covers 20/20 exams, while expert alignment review remains 0/20.
