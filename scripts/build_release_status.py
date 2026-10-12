"""Publish requirement-level status; never infer whole-project completion from tests."""
import html
import json
from pathlib import Path
from neurofusion.data import save_json
from neurofusion.qualification import qualification_gates

root=Path(__file__).resolve().parents[1]
scope=json.loads((root/'configs/release_scope.json').read_text(encoding='utf-8'))
rows=[
 ('foundation','Repository, GPU environment and data pipeline','implemented','README.md','Maintain reproducible environments and verify on a clean machine.'),
 ('local_app','Local uploads, jobs, history and reports','implemented','docs/LOCAL_VIEWER.md','Local prototype; public deployment is tracked separately.'),
 ('tumor','Tumor classification and segmentation','partial','docs/TUMOR_QUALIFICATION.md','All three improved segmenters passed compatibility and development uncertainty checks. Classifier recalibration rejected; unchanged probabilities pass limited development checks (docs/TUMOR_CLASSIFIER_UNCERTAINTY.md). Patient independence and segmentation screening specificity remain unestablished; no promotion.'),
 ('stroke','Stroke segmentation','partial','docs/STROKE_ZERO_OVERLAP.md','0.65 rechecked and rejected: three newly zero-Dice patients. Fixed 0.55/component-filter correction passes 7/8 strengthened checks but still newly misses one patient. Baseline retained; improved candidate and cross-seed/independent confirmation remain.'),
 ('ucsf','UCSF tumor specialist','partial','docs/UCSF_REFINEMENT.md','Three-seed fixed refinement completed: seed 44 improves Dice and false positives, but seeds 42/43 fail. Repeatable development improvement and original qualification remain unmet; no promotion.'),
 ('acquisition','New UCSF acquisition and integrity','implemented','docs/UCSF_ACQUISITION.md','20 pairs verified; independence tracked separately.'),
 ('leakage','Patient identity and overlap audit/disposition','implemented','docs/DATA_INDEPENDENCE.md','User-requested resolve-or-document task complete across four local collections. Eight issues have explicit dispositions; unknown patient/cross-source exposure remains documented. Independence is not certified; the separate evaluation gate remains open.'),
 ('review_tool','Full-volume source-linked review workbench','implemented','docs/COHORT_REVIEW_WORKBENCH.md','Local self-entered reviewer identities; does not certify expertise.'),
 ('fusion','Early, feature and ensemble fusion comparisons','partial','docs/FUSION_NONREGRESSION.md','Weighted candidates failed improvement/no-new-miss checks. Experimental CLI now defaults to exact DWI baseline; ensemble requires explicit flag. ADC-only disabled. Better fusion candidates and independent evaluation remain.'),
 ('uncertainty','Calibration and abstention','partial','docs/UNCERTAINTY_DECISIONS.md','Explicit reliability abstention integrated into inference, viewer and reports; classifier development cutoff bound to its checkpoint. Qualified coverage remains zero; useful independently reliable calibration/abstention is not established.'),
 ('robustness','Robustness experiment lab','implemented','docs/SEGMENTATION_ROBUSTNESS.md','Requested extension completed: 721 tumor segmentation images and 37 DWI volumes under six conditions each, with hashed predictions and exact metric replay. Perturbation failures remain model-quality findings; independent scanner/site robustness is not established.'),
 ('evidence','Findings, physical coordinates and evidence links','implemented','docs/MEASUREMENTS_AND_EVIDENCE.md','Validated physical volumes, original/canonical coordinates and source-bound finding links for the supported DWI/tumor paths. 49 synthetic geometries and 37 development volumes checked. Pixel-only tumor images; clinical mask accuracy and atlas/longitudinal registration are not claimed.'),
 ('collaboration','Authenticated collaboration and adjudication','implemented','docs/COLLABORATIVE_REVIEW.md','Local accounts, two-reviewer assignments, blind mask uploads, adjudication and approved exports implemented. Requires real accounts/reviewers; remote deployment and correction rounds remain out of scope.'),
 ('active','Active learning','implemented','docs/ACTIVE_LEARNING.md','Selection connected to assignments, effort reports, adjudication and exports. Three-seed retrospective equal-budget benchmark complete: active Dice 0.2982 vs random 0.3354. Prospective human-time efficiency remains unproven.'),
 ('promotion','Retraining and model promotion','implemented','docs/MODEL_PROMOTION.md','Versioned labels, approved-export ingestion, three-architecture retraining, coverage and prediction evidence, acceptance assembly and reversible registry updates implemented. Real BRISC candidate rejected; baseline retained. Scientific gates are unchanged.'),
 ('ct','CT hemorrhage specialist','partial','docs/ADDITIONAL_SPECIALISTS.md','DICOM/label adapter and six-label CNN training pipeline implemented. Authorized CT data absent; no real CT training or evaluation.'),
 ('vascular','Vascular and small-lesion specialists','partial','docs/ADDITIONAL_SPECIALISTS.md','Physical-coordinate target checks implemented. No acquired vascular data or trained detector; other small-lesion branches remain planned.'),
 ('longitudinal','Longitudinal analysis','partial','docs/ADDITIONAL_SPECIALISTS.md','Registered-mask volume-change checks implemented. Matched visits, verified registration, learned models and real-data evaluation remain.'),
 ('eeg','EEG event detection','partial','docs/ADDITIONAL_SPECIALISTS.md','CHB-MIT pilot trained/evaluated: 4/4 seizures matched but 722 false alarms (~72/background hour). Not suitable for adoption; expand data and reduce false alarms.'),
 ('cohort_research','Matched multimodal cohort research','planned','NeuroFusion_Project_Manual.md','Compatible same-patient modalities and predefined endpoints.'),
 ('federated','Federated simulation','partial','docs/FEDERATED_SYSTEM_CHECKS.md','Expanded recovery, serialized communication integrity/byte accounting and all four development evaluations verified. Partial delivery and committed recovery reproduce final weights exactly. Untouched evaluation remains unmet; no real-network/privacy qualification.'),
 ('evaluation','Frozen independent evaluation','pending','docs/FINAL_EVALUATION_READINESS.md','Seven numeric engineering targets finalized and hash-bound; eligibility audit found zero cleared models. Executable protocol remains blocked by model-quality, cohort eligibility and justified acceptance prerequisites. No protected inference or independent completion claimed.'),
 ('deployment','Deployment and maintenance','partial','docs/LOCAL_RELEASE.md','Offline wheel installation and three-model loading verified in a fresh directory using existing host dependencies; loopback HTTP checks passed. 173 private viewer files and two databases recovered; one-shot monitoring verified and flags one historical input rejection. Clean-machine installation and off-device disaster recovery remain unverified; public hosting is not enabled.'),
]
records=[dict(id=i,name=n,status=s,evidence=e,remaining=r) for i,n,s,e,r in rows]
records=[r for r in records if r['id'] not in scope['removed_requirement_ids']]
for r in records:
 if r['id']=='eeg':
  r['evidence']='docs/EEG_FALSE_ALARM_REDUCTION.md'
  r['remaining']='Existing 12 recordings: two-window confirmation reduces false alarms 722 to 591 (18.14%) and retains 4/4 development matches, but 59.3/hour remains excessive. Three retrained seeds missed 3/4 seizures and were rejected. A useful sensitivity/false-alarm tradeoff and independent reliability remain unmet; no downloads.'
historical=json.loads((root/'experiments/ucsf-acquisition-001/qualification.json').read_text(encoding='utf-8'))
qualification=qualification_gates(historical['evidence'])
qualification['scope_change']='2026-10-10: user removed mandatory expert review; no expert review claimed'
save_json(root/'docs/research_qualification.json',qualification)
for r in records:
 if not (root/r['evidence']).is_file():raise ValueError('Missing evidence '+r['evidence'])
counts={s:sum(r['status']==s for r in records) for s in sorted({r['status'] for r in records})}
progress_path=root/'docs/progress_tracker.json'
progress=json.loads(progress_path.read_text(encoding='utf-8'))
robustness_verification=json.loads((root/'experiments/segmentation-robustness-001/verification.json').read_text())
if not robustness_verification['passed']:raise ValueError('Robustness replay must pass before closure')
progress['updated']='2026-10-12'
federated_verification=json.loads((root/'experiments/federated-system-verification-002/summary.json').read_text())
if not federated_verification['passed']:raise ValueError('Federated system checks failed')
progress['federated_system_checks']={'status':'partial','local_system_checks_complete':True,
 'recovery_exact':True,'communication_checks_complete':True,'development_evaluations_reproduced':4,
 'untouched_evaluation_complete':False,'evidence':'docs/FEDERATED_SYSTEM_CHECKS.md'}
eeg_reduction=json.loads((root/'experiments/eeg-conservative-001/summary.json').read_text())
progress['eeg_false_alarm_reduction']={'status':'partial','evidence':'docs/EEG_FALSE_ALARM_REDUCTION.md',
 'baseline_false_alarms':722,'conservative_false_alarms':591,'matched_events':4,'reference_events':4,
 'false_alarms_per_background_hour':eeg_reduction['candidate']['false_alarms_per_background_hour'],
 'excessive_false_alarms_resolved':False,'three_retrained_candidates_rejected':True,
 'independently_qualified':False}
measurement_verification=json.loads((root/'experiments/measurement-verification-001/summary.json').read_text())
if not measurement_verification['passed']:raise ValueError('Measurement verification must pass before closure')
progress['measurements_and_evidence']={'status':'implemented','evidence':'docs/MEASUREMENTS_AND_EVIDENCE.md',
 'validation_volumes':measurement_verification['validation_volumes'],
 'components_verified':measurement_verification['components_verified'],
 'clinical_measurement_accuracy_established':False}
progress['segmentation_robustness']={'status':'implemented','testing_extension_complete':True,
 'tumor_validation_images':721,'stroke_validation_volumes':37,'conditions_per_task':6,
 'paired_metrics_replayed':robustness_verification['paired_metrics_replayed'],
 'perturbation_failures_resolved':False,'independent_robustness_established':False,
 'evidence':'docs/SEGMENTATION_ROBUSTNESS.md'}
progress['model_promotion']={'status':'implemented','registry_and_rollback_implemented':True,
 'inference_registry_integrated':True,'candidate_promoted':False,
 'evidence':'docs/MODEL_PROMOTION.md',
 'remaining':'Software integration complete; actual candidate acceptance remains unmet and no candidate promoted'}
progress['requirement_counts']=counts
independence_closure=root/'experiments/data-independence-closure-001/verification.json'
if independence_closure.is_file():
 progress['data_independence_disposition']={'documentation_complete':True,
  'independence_certified':False,'issues_with_dispositions':8,
  'evidence':'docs/DATA_INDEPENDENCE.md',
  'completion_basis':'Explicit user request to resolve OR document uncertain identities and possible overlap; not a passed independent-evaluation gate'}
stroke_audit=root/'experiments/stroke-zero-overlap-001/verification.json'
if stroke_audit.is_file():
 progress['stroke_zero_overlap_audit']={'status':'completed_with_rejection',
  'threshold_065_accepted':False,'fixed_correction_accepted':False,
  'new_misses_065':3,'new_misses_correction':1,
  'active_model_changed':False,'cross_seed_confirmation':False,
  'evidence':'docs/STROKE_ZERO_OVERLAP.md'}
classifier_followup=root/'experiments/tumor-classifier-uncertainty-003/verification.json'
if classifier_followup.is_file():
 progress['tumor_classifier_uncertainty_followup']={
  'evidence':'docs/TUMOR_CLASSIFIER_UNCERTAINTY.md',
  'recalibration_rejected':True,'original_probabilities_retained':True,
  'limited_development_checks_passed':True,'calibration_improvement_demonstrated':False,
  'independent_qualification':False,'model_promoted':False}
save_json(progress_path,progress)
save_json(root/'docs/release_status.json',{'updated':'2026-10-12','scope':scope['scope'],
 'overall_percent':None,'counts':counts,'research_release_complete':False,'clinical_ready':False,
 'scope_change':{'date':'2026-10-10','previous_groups':23,'current_groups':len(records),'previously_removed':['expert'],'removed_requirement_ids':scope['removed_requirement_ids'],'reason':scope['reason']},
 'dataset_downloads_allowed':False,
 'note':'Requirement groups are unequal in effort. Implemented means working software/data capability, not clinical validation. No weighted completion percentage is established.', 'requirements':records})
table=''.join('<tr><td>'+html.escape(r['name'])+'</td><td><span class="'+r['status']+'">'+r['status'].replace('_',' ')+'</span></td><td>'+html.escape(r['remaining'])+'</td></tr>' for r in records)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NeuroFusion release roadmap</title><style>:root{color-scheme:dark}body{font:16px system-ui;background:#0b1726;color:#e5eef8;max-width:1200px;margin:30px auto;padding:20px}a{color:#80ded0}h1{font-size:34px}.cards{display:flex;gap:16px;flex-wrap:wrap}.card{background:#14273b;border:1px solid #34516d;border-radius:12px;padding:20px;flex:1;min-width:170px}strong{font-size:28px;display:block}table{border-collapse:collapse;width:100%;margin-top:22px}td,th{padding:16px;text-align:left;border-bottom:1px solid #34516d;vertical-align:top}.implemented{color:#80ded0}.partial{color:#f7ce85}.requires_human{color:#c8a9ff}.scroll{overflow:auto}</style><a href="/">← Workspace</a><h1>Full research release roadmap</h1><p>The project is still in development. These are requirement groups, not equal amounts of work; their counts are not an overall completion percentage.</p><div class="cards">'''
page+=''.join(f'<div class="card"><strong>{count}</strong>{state.replace("_"," ")}</div>' for state,count in counts.items())
page+=f'</div><p><b>Existing data only. Dataset downloads disabled.</b> BRISC, ISLES, local UCSF and the 12-recording CHB-MIT pilot are retained. New-data specialist branches are removed from the plan. The baseline changes explicitly from 23 to {len(records)} groups; removed scope is not completed work.</p><p>UCSF research qualification: {qualification["passed"]}/{qualification["total"]} gates passed. Expert review remains optional. Failed scientific checks are not waived.</p><p><a href="/cohort-review">Optional full-volume review</a> · <a href="/api/release-status">Download requirement status JSON</a></p><div class="scroll"><table><tr><th>Requirement</th><th>Status</th><th>Remaining work / scope</th></tr>'+table+'</table></div><p>Full release, independent performance, and clinical readiness have not been established.</p></html>'
(root/'viewer/release-status.html').write_text(page,encoding='utf-8')
print(json.dumps(counts))

# A separately verified delivery contract closes the revised research-app scope.
# The original quality statuses above remain visible and are never converted to passes.
delivery_path=root/'docs/research_delivery.json'
if delivery_path.is_file() and scope.get('completion_definition')=='local_research_application':
 from neurofusion.research_release import accept_delivery
 delivery=json.loads(delivery_path.read_text(encoding='utf-8'))
 accept_delivery(root,records,delivery['requirements'],delivery['checks'],delivery['evidence'])
 status=json.loads((root/'docs/release_status.json').read_text())
 status.update(overall_percent=100,research_release_complete=True,completion_definition='Local research application delivery; not model qualification',
  delivery_counts={'closed':len(records),'total':len(records)},
  note='100% of the user-approved research application delivery scope. Original scientific/quality statuses and failed checks remain visible; clinical readiness is false.',
  delivery_evidence='docs/research_delivery.json')
 save_json(root/'docs/release_status.json',status)
 progress.update(research_application_complete=True,research_delivery_percent=100,all_models_qualified=False,
                 completion_definition=scope['completion_definition'])
 save_json(progress_path,progress)
 page=page.replace('Full research release roadmap','Completed local research application')
 page=page.replace('The project is still in development. These are requirement groups, not equal amounts of work; their counts are not an overall completion percentage.',
  'Research application delivery: <b>100% — '+str(len(records))+'/'+str(len(records))+' outcomes delivered or documented with restrictions.</b> The user accepted this completion definition on 12 October 2026. The counts below preserve original implementation and scientific qualification status; they are not the delivery progress bar.')
 page=page.replace('Remaining work / scope','Scientific limitations / scope')
 page=page.replace('Full release, independent performance, and clinical readiness have not been established.',
  'Local research application delivery is complete. Model qualification, independent performance, clean-machine installation, off-device recovery and clinical readiness are not established.')
 (root/'viewer/release-status.html').write_text(page,encoding='utf-8')
