"""Conservative evidence-based qualification and acquisition planning helpers."""
import hashlib


def acquisition_queue(inventory, development_patients, count=20, salt='ucsf-qualification-intake-v1'):
    rows=inventory['patients'];seen=set();eligible=[]
    for row in rows:
        patient=row['patient_id']
        if patient in seen:raise ValueError('Duplicate patient inventory')
        seen.add(patient)
        if patient in development_patients or row.get('development_patient') or row.get('brats21_ids') or row.get('exclusion_reasons') or not row.get('candidate'):continue
        eligible.append(row)
    if count<=0 or count>len(eligible):raise ValueError('Invalid acquisition queue size')
    ranked=sorted(eligible,key=lambda r:(hashlib.sha256((salt+':'+r['patient_id']).encode()).hexdigest(),r['patient_id']))
    return {'purpose':'provisional acquisition planning; not a frozen or independent test cohort','salt':salt,'eligible_patients':len(eligible),'selected_patients':count,'independence_verified':False,'cohort_frozen':False,'records':[{'patient_id':r['patient_id'],'exam_id':r['baseline_exam_id'],'files':[f"{r['baseline_exam_id']}_T1c.nii.gz",f"{r['baseline_exam_id']}_tumor_segmentation.nii.gz"],'status':'not_acquired_or_verified','independence_verified':False} for r in ranked[:count]]}


def qualification_gates(evidence, *, require_expert_review=False):
    # Missing evidence fails closed; completion of an experiment is not a pass.
    checks=[('development_reproducibility',evidence.get('reproducibility_verified') is True),
            ('development_performance',evidence.get('all_seeds_passed') is True),
            ('target_contract',evidence.get('target_contract_signed') is True),
            ('cohort_independence',evidence.get('independence_verified') is True),
            ('acquisition_integrity',evidence.get('all_external_files_verified') is True),
            ('frozen_evaluation_protocol',evidence.get('evaluation_protocol_frozen') is True),
            ('independent_performance',evidence.get('independent_performance_passed') is True),
            ('application_integration',evidence.get('candidate_integration_verified') is True),
            ('release_review',evidence.get('release_review_signed') is True)]
    if require_expert_review:checks.insert(5,('expert_alignment_review',evidence.get('expert_review_complete') is True))
    return {'scope':'UCSF specialist research qualification; not whole project or clinical approval','expert_review_required':require_expert_review,'gates':[{'id':key,'passed':passed} for key,passed in checks],'passed':sum(p for _,p in checks),'total':len(checks),'qualified_for_research_release':all(p for _,p in checks),'clinical_ready':False}
