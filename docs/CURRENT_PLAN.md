> **12 October 2026 completion amendment:** The user accepted delivery of the local research application with documented model limitations. [Final delivery definition and run instructions](RESEARCH_RELEASE_COMPLETE.md) supersede historical finish criteria below. Model qualification, independent evaluation and clinical readiness are not claimed. The generated release status records verified delivery acceptance.

# NeuroFusion: existing-data completion plan

This is the authoritative plan following the user's 10 October 2026 instruction:
remove missing datasets, use only data already owned, and download nothing.
It supersedes acquisition and expansion instructions in the original manual,
PDF and historical research reports. Historical results and source attribution
remain intact; excluded capabilities are not described as completed.

## Fixed data and supported work

| Local collection | Work retained | Boundary |
| --- | --- | --- |
| BRISC v6 | Tumor image classification and segmentation | 2D supported images; patient independence unresolved |
| ISLES 2022 | DWI stroke segmentation, matched DWI/ADC fusion research | Existing partitions only; protected holdout remains protected |
| UCSF-PDGM v5 local subset | Tumor specialist development and existing cohort checks | Failed specialist qualification remains failed; no additional acquisition |
| CHB-MIT local pilot | EEG event detection research | 12 existing EDF recordings; excessive false alarms, no deployment as a seizure detector |

RSNA ICH, RSNA aneurysm, MSSEG-2, VALDO, ATLAS, BraTS-METS,
BraTS-PEDs, WMH Challenge, CQ500, ADNI and further CHB-MIT recordings
are removed from the plan. CT, vascular/small-lesion, longitudinal and
additional matched-cohort specialist requirements are removed because the
necessary data is absent. Their existing utility code is retained but is not
an advertised trained capability. No cross-patient multimodal fusion is allowed.

## Finish order

1. Apply the existing-data scope to configuration, roadmap and documentation;
   disable acquisition entry points.
2. Verify the existing application, local models and release archive, keeping
   the current working environment and all private files intact.
3. Complete candidate promotion/rollback controls and remaining retained
   integration, measurement and robustness checks using current data only.
4. Address retained model-quality and uncertainty failures with fixed protocols
   and existing development partitions. A failed experiment stays failed; no
   promised score or automatic promotion.
5. Freeze an eligible evaluation protocol only when its prerequisites hold.
   Unverifiable identities cannot be repaired by relabeling a cohort independent.
6. Close release acceptance only with evidence. Expert review is optional.

No additional data acquisition, condition coverage or requirement groups are
needed. The current software can be used locally while remaining scientific
acceptance work is recorded in `docs/release_status.json`.

## Run the existing application

In PowerShell:

```powershell
Set-Location D:\NeuroFusion
& .\.venv-neurofusion\Scripts\python.exe scripts\serve_viewer.py --port 8766
```

Open http://127.0.0.1:8766/. If that port already serves NeuroFusion, use the
running instance. The viewer offers BRISC-style tumor images and DWI volumes;
UCSF, fusion and EEG experiments are research evidence, not additional upload
inference modes. Do not install packages or run acquisition scripts as part of
this offline completion task. Use the already configured environment.

## Progress definition

The baseline changes explicitly from 23 to 19 requirement groups. This is a
scope reduction, not four completed tasks. Software verification, model quality
and independent qualification are reported separately. Full completion is not
100% until the retained acceptance requirements are satisfied.
