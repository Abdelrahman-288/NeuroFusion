> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# NeuroFusion scope freeze

## Explicit amendment: mandatory expert review removed

On 10 October 2026 the user requested: "no need for expert review remove this part". The `expert` requirement is removed from the completion baseline, changing **24 groups to 23**. Expert review is optional and is not counted as passed or performed. This amendment supersedes the original count below. Existing review software remains available. Model quality, automated data checks, independence checks, evaluation protocol freeze and technical release checks remain required. Future reports must identify this scope change rather than describe the denominator reduction as completed work.

User decision recorded 10 October 2026: finish the existing project before expanding it. Do not add new features, specialist branches, experiments unrelated to acceptance, or requirement groups during this release.

## Fixed baseline

The baseline is the 24 requirement groups in `docs/release_status.json` on 10 October 2026:

`foundation`, `local_app`, `tumor`, `stroke`, `ucsf`, `acquisition`, `leakage`, `review_tool`, `expert`, `fusion`, `uncertainty`, `robustness`, `evidence`, `collaboration`, `active`, `promotion`, `ct`, `vascular`, `longitudinal`, `eeg`, `cohort_research`, `federated`, `evaluation`, `deployment`.

Do not silently remove, defer, split, or add groups to change the apparent completion rate. In particular, the suggested smaller v1/v2 split was not explicitly accepted. Existing unfinished specialist and research requirements remain in scope.

Necessary fixes, data preparation, training, integration, documentation and verification may proceed within these groups. Subtasks may explain existing work without increasing the baseline denominator. Future feature ideas wait until this release is complete unless the user explicitly changes the scope.

## Completion reporting

- Report implemented software separately from demonstrated model quality and independent evaluation.
- Count a group as implemented only with its documented evidence and material limitations. Do not equate a software status with successful clinical or independent qualification.
- Retain the fixed 24-group denominator. The current 6/24 implemented count is a requirement-count metric, not an effort-weighted project percentage.
- Do not invent a new overall completion estimate or reinterpret earlier estimates as measured progress.
- Identify actual dependencies: authorized datasets, unmet performance gates and deployment decisions. Missing dependencies remain incomplete; do not fabricate approvals or lower acceptance checks to finish. Expert review is optional under the explicit amendment above.
- The objective is completion of the existing research platform. Research release completion does not itself establish suitability for clinical diagnosis.

## Execution priority

Complete and verify existing integration and release controls, then address the recorded model/data/evaluation gaps and deployment requirements. Reuse existing pipelines and evidence. Run additional experiments only to resolve a documented acceptance gap. Keep `docs/release_status.json` as the fixed-scope requirement tracker, with evidence for every status change.
