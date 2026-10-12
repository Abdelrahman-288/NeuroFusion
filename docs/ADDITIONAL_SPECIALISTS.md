> **Current scope (10 October 2026):** Existing local BRISC, ISLES, UCSF and 12-recording CHB-MIT pilot only. Missing datasets and their specialist branches are removed; no downloads. [Current completion plan](CURRENT_PLAN.md) supersedes historical acquisition and expansion steps below. Failed quality checks remain failed.

# Additional specialist branches

**12 October 2026 EEG update:** A conservative two-window rule reduced false alarms from 722 to 591 while retaining 4/4 existing validation matches. 59.3 false alarms/background hour remains excessive. Three normalized retraining candidates missed three seizures and were rejected. See [EEG false-alarm reduction](EEG_FALSE_ALARM_REDUCTION.md). The current scope remains the 12 recordings already owned; historical acquisition suggestions below are superseded.

Updated 10 October 2026. These are separate tasks, with separate data, models and evaluations. No additional specialist is independently qualified. The user confirmed no additional CT/vascular/longitudinal data is currently available.

| Branch | State | Remaining |
|---|---|---|
| CT hemorrhage | adapter_and_training_pipeline_implemented | Authorized CT data absent; six-label CNN training pipeline implemented but no real training/evaluation performed |
| Vascular / aneurysm | coordinate_validation_tested | No acquired images, locations, masks or patient mapping; MIRA access not verified |
| EEG seizure | trained_pilot_evaluated | Six-patient label-selected pilot only. Expand cohort/recordings, assess event false alarms and latency, and perform independent qualification. |
| Longitudinal lesion change | measurement_checks_tested | No matched longitudinal source cohort or registration ground truth; no learned model |
| Brain metastases | planned | Data, license/access, training and evaluation absent |
| Pediatric tumor | planned | Separate population-specific data and qualification required |
| Established stroke | planned | Data and chronicity/target contract required |
| White matter hyperintensities | planned | No acquired data or evaluated specialist |
| Cerebral microbleeds | planned | No acquired data or evaluated specialist |
| Lacunes | planned | No acquired data or evaluated specialist |
| Perivascular spaces | planned | No acquired data or evaluated specialist |
| Atrophy and neurodegeneration research | planned | Access approval, matched cohort and defined endpoint required |
| CT mass effect / fracture | planned | Data access, study identities and independent development data required |

## Implemented and tested tools
- `scripts/import_ct_hemorrhage.py --dicom-root PATH --labels CSV --output FRESH_FOLDER`: validates complete six-label targets, CT/HU preparation and patient grouping. Requires authorized local data. Then use `scripts/train_ct_hemorrhage.py --manifest IMPORT/manifest.json --output FRESH_RUN` for the implemented six-output CT CNN baseline. The trainer rejects patient leakage and never loads holdout arrays. No real CT training has occurred because the dataset is absent.
- `src/neurofusion/specialist_inputs.py`: validates CTA/MRA physical target locations and computes registered same-patient binary mask change. Millimeter units are required. Neither is a learned aneurysm or new-lesion detector.
- `scripts/train_eeg_pilot.py` and `verify_eeg_pilot.py`: six-channel temporal CNN, patient-separated training/validation and event metrics. Re-run only with a fresh experiment configuration; existing evidence is preserved.

## EEG dataset and limitations
Official CHB-MIT v1.0.0: https://physionet.org/content/chbmit/1.0.0/ . Open Data Commons Attribution License v1.0. Cite Guttag (2010), DOI 10.13026/C2K01R, and Shoeb (2009). Source records checked against publisher SHA256. Downloads use the official public physionet-open S3 mirror with validated byte ranges.

Cases chb01–chb04 train; chb05–chb06 validate. First lexicographic seizure-free and seizure-containing recording per case. Case chb21 is known to be the same patient as chb01 and is mapped accordingly. No random window split across a patient. Positive selection enriches the cohort: pilot event sensitivity and false alarms cannot be extrapolated to a general screening population.

Fixed 4-second nonoverlapping windows; six bipolar channels; causal 0.5–40 Hz filtering and decimation from 256 to 128 Hz; no normalization fit on validation. Final epoch 10, fixed threshold 0.5. Alarms require window-end observation. Matching uses positive window-interval overlap, so a detection can arrive after a short seizure ends. Latencies must not be interpreted as zero-delay detection.

## Data access and branch requirements
RSNA ICH data: https://www.kaggle.com/c/rsna-intracranial-hemorrhage-detection/data . Access subject to competition/data-use terms; full archive is large. Obtain permitted data, retain source metadata and patient/exam identities, audit duplicates, then train and evaluate six-label classification. Do not claim segmentation from image-level labels.

RSNA aneurysm source: https://mira.rsna.org/dataset/7 . Download access was not verified here. Require approved modality/label contract, physical coordinate semantics, patient mapping, negatives and localization references before training.

Longitudinal: matched visits, dates/order, consistent labels and independently checked registration are prerequisites. MSSEG-2 is a candidate source (https://portal.fli-iam.irisa.fr/msseg-2/); no access was verified. Existing unrelated MRI subjects cannot be converted into longitudinal pairs.

Other planned datasets/targets retain their contracts in configs/additional_specialists.json. No placeholder or randomly initialized network counts as a trained specialist.

## Next work
Obtain authorized CT and vascular data; acquire verified longitudinal pairs; expand EEG beyond this pilot. For each branch, freeze patient-disjoint roles and evaluation definitions before training. Record every failed result, calibration limits and independently tested performance before integration.

## Measured EEG pilot result
Matched events: 4/4; false alarms/background hour: 72.456. Validation recording hours: 10.01. Independent qualification: false.

Quality decision: the EEG pilot is not suitable for adoption because its 722 false alarms are excessive. The 4/4 matched events occur in only two validation patients and do not establish generalization. All 262 software tests passed, and the final EEG checkpoint reproduced all four validation-recording probability arrays and event counts. Existing application models remain unchanged.
