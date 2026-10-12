"""Finalize engineering target definitions and snapshot honest evaluation eligibility."""
import argparse,json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.final_evaluation import eligibility,require_executable

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=False)
specs=[
 ('tumor_classifier','BRISC 2D grayscale image; four publisher classes glioma, meningioma, pituitary, no_tumor; argmax; no_tumor is not healthy',
  'docs/TUMOR_CLASSIFIER_UNCERTAINTY.md','Patient IDs unavailable; development calibration does not establish new-patient reliability.'),
 ('tumor_segmenter','BRISC tumor-positive 2D images; supplied grayscale labels <=10 background, >=246 foreground; reject intermediate labels; probability >=0.5 at original image dimensions',
  'docs/TUMOR_QUALIFICATION.md','Image groups are not verified patients; no qualified screening specificity or final patient-independent cohort.'),
 ('stroke_dwi','ISLES single 3D DWI; binary supplied lesion mask; canonical orientation and nonzero zscore; probability >=0.5 restored to source grid',
  'docs/STROKE_ZERO_OVERLAP.md','Improved threshold/candidate failed no-new-zero-overlap checks; independent qualification not established.'),
 ('ucsf_specialist','UCSF-PDGM v5 T1c only; engineering foreground union of numeric labels {1,2,4}, background 0; no clinical compartment names; native-grid probability threshold 0.5',
  'docs/UCSF_REFINEMENT.md','Repeated development performance failed; source/exposure limitations remain; no eligible specialist selected.'),
 ('fusion','Matched same-patient ISLES DWI/ADC; binary lesion mask, threshold 0.5; ADC-only excluded',
  'docs/FUSION_NONREGRESSION.md','Fusion candidates failed to improve on DWI without new misses; baseline fallback is not a qualified fusion candidate.'),
 ('eeg','CHB-MIT six-channel 4-second window probabilities; original CNN threshold 0.5 with causal two-window confirmation; event overlap and decision-availability metrics reported separately',
  'docs/EEG_FALSE_ALARM_REDUCTION.md','All 12 recordings already assigned to development; no untouched EEG subset; 59.3 false alarms per background hour remains excessive.'),
 ('federated','UCSF T1c numeric-foreground segmentation at fixed 120x120 model grid, threshold 0.5, simulated clients; preserve historical metric separately from any native-grid measurement',
  'docs/FEDERATED_SYSTEM_CHECKS.md','Four evaluation patients were reused development cases; no independently qualified UCSF candidate or untouched-evaluation eligibility.')]
targets=[];models=[];bindings={}
for key,target,evidence,reason in specs:
    file=root/evidence;bindings[evidence]=digest(file)
    targets.append(dict(model_key=key,target=target,clinical_label_certification=False))
    checks=dict(target_defined=True,development_passed=False,compatible_input=True,cohort_eligible=False,acceptance_criteria_justified=False)
    models.append(dict(model_key=key,checks=checks,**eligibility(checks),reason=reason,evidence=dict(path=evidence,sha256=digest(file))))
targetpath=a.output/'targets.json';save_json(targetpath,dict(version=1,status='FROZEN_ENGINEERING_TARGET_DEFINITIONS',targets=targets,
    amendment_rule='New target definitions require a new version; this record is not an executable model evaluation protocol'))
for path in ['docs/research_qualification.json','docs/DATA_INDEPENDENCE.md','experiments/data-independence-closure-001/verification.json','experiments/ucsf-acquisition-001/summary.json',
             'experiments/isles-curated-001/frozen-splits-v1.json','experiments/brisc-curated-001/splits.json','experiments/eeg-pilot-001/prepared-manifest.json']:
    bindings[path]=digest(root/path)
protocol=dict(schema_version=1,status='BLOCKED_NOT_FROZEN_FOR_EXECUTION',models=models,eligible_models=[],
    target_definitions=dict(path=targetpath.resolve().relative_to(root).as_posix(),sha256=digest(targetpath)),
    expert_review_required=False,downloads_allowed=False,protected_inference_performed=False,
    statistics_plan=dict(segmentation=['per-case Dice','zero-overlap cases','false-positive mL where geometry permits','absolute volume error mL'],
        classification=['accuracy','macro F1','per-class sensitivity','confusion matrix'],
        eeg=['one-to-one event matches','timely matches','false alarms/background hour','background time in alarm','decision latency'],
        aggregation='Equal patient weighting only where identities are verified; do not substitute image groups for patients',
        confidence_intervals='Patient bootstrap, 2000 samples, fixed seed 20261012; describe convenience-cohort and small-sample limitations',
        acceptance='No clinical or release cutoff invented after observing test outputs; justify and freeze task-specific criteria before inference'),
    execution_requirements=['Bind qualified checkpoint and preprocessing hashes','Bind eligible patient inventory and explicit pre-inference exclusions',
        'Set justified acceptance criteria and metrics before inference','Save protocol hash before first prediction; no tuning or patient reselection on test results',
        'Report all cases and failed criteria; audit any restart against saved prediction hashes'],
    disposition='No models eligible under existing prerequisites; protected cohorts remain unused')
save_json(a.output/'protocol-readiness.json',protocol)
try:require_executable(protocol)
except ValueError:blocked=True
else:raise RuntimeError('Blocked protocol incorrectly allowed execution')
save_json(a.output/'evidence-hashes.json',bindings)
save_json(a.output/'verification.json',dict(passed=all(digest(root/k)==v for k,v in bindings.items()),
    blocked_execution_rejected=blocked,target_definitions_sha256=digest(targetpath),
    protocol_sha256=digest(a.output/'protocol-readiness.json'),eligible_models=0,models_audited=len(models),
    final_evaluation_complete=False,independent_inference_performed=False))
print('Finalized seven engineering target definitions; zero eligible models. Protected inference blocked.')
