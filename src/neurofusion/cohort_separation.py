"""Patient-level development exclusions and conservative external candidate inventory."""
from collections import defaultdict


def audit_separation(records, development_exam_ids):
    by_exam = {r['exam_id']: r for r in records}
    if len(by_exam) != len(records):
        raise ValueError('Duplicate exam identity')
    development = set(development_exam_ids)
    if not development or not development.issubset(by_exam):
        raise ValueError('Development exam IDs must be nonempty and known')
    by_patient = defaultdict(list)
    for record in records:
        by_patient[record['patient_id']].append(record)
    development_patients = {by_exam[x]['patient_id'] for x in development}
    patients = []
    for patient, exams in sorted(by_patient.items()):
        baselines = [r for r in exams if r['followup_days'] is None]
        if len(baselines) != 1:
            raise ValueError('Each patient must have exactly one baseline')
        mappings = sorted({r['brats21_id'] for r in exams if r['brats21_id']})
        reasons = []
        if patient in development_patients:
            reasons.append('development_patient_including_all_followups')
        if mappings:
            reasons.append('recorded_brats21_mapping_conservative_exclusion')
        patients.append({'patient_id':patient, 'baseline_exam_id':baselines[0]['exam_id'],
            'all_exam_ids':sorted(r['exam_id'] for r in exams), 'brats21_ids':mappings,
            'development_patient':patient in development_patients,
            'candidate':not reasons, 'exclusion_reasons':reasons,
            'independence_verified':False})
    return {'policy':'Exclude all development-patient exams and any patient with a recorded BraTS mapping; inventory only',
        'note':'A missing mapping does not prove independence. BraTS exclusion is conservative, not evidence the current model trained on BraTS.',
        'evaluation_ready':False, 'cohort_frozen':False,
        'total_patients':len(patients), 'development_patients':len(development_patients),
        'development_patients_with_brats_mapping':sum(p['development_patient'] and bool(p['brats21_ids']) for p in patients),
        'development_patient_exams_excluded':sum(len(p['all_exam_ids']) for p in patients if p['development_patient']),
        'patients_with_brats_mapping':sum(bool(p['brats21_ids']) for p in patients),
        'candidate_patients':sum(p['candidate'] for p in patients), 'patients':patients}
