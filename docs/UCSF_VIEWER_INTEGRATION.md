# UCSF review workspace integration

2026-10-08. The existing local viewer now links acquisition results, cohort-wide
resolution QA, original-grid alignment gallery, candidate target contract and
patient/source separation. Each is explicitly labeled as a dated research snapshot.
Pending expert reviews, semantic confirmation, model compatibility and independence
are displayed beside the links. No review was marked approved and no inference ran.

The viewer server serves these under /research/ucsf/{pilot,resolution,alignment,
targets,separation}/. Explicit report-file allowlists and constrained case/image
paths retain nested report links and all gallery PNGs. Canonical path containment
prevents escapes; unknown paths and raw arrays remain inaccessible through these
routes. Missing artifacts return 404. The original metadata-intake report remains
available at its historical route.

Validation: 180 full-suite tests passed in 36.52 seconds, including HTTP checks
for supported summaries, nested case reports, unknown files and encoded traversal.
A separate temporary server on port 8772 verified all five report pages, 389 linked
local assets, and the viewer section text. It had no inference worker. Browser
visual inspection was unavailable this turn; the earlier gallery's visual and
overlay checks remain documented separately. Verification evidence is in
experiments/ucsf-viewer-integration-001/verification.json.

Use the normal viewer launch command after restarting your existing viewer server
to load the route changes: .\.venv-neurofusion\Scripts\python.exe scripts/serve_viewer.py
The verification server is not the application and has been stopped after checking.

Next: resolve semantic/model-target compatibility and expert alignment review
before independent evaluation. These report links make evidence accessible but do
not satisfy those scientific review gates. Overall scope estimate remains ~83%.
