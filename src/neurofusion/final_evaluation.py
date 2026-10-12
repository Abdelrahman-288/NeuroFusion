"""Fail-closed final-evaluation eligibility, separate from a model's test results."""
REQUIRED=('target_defined','development_passed','compatible_input','cohort_eligible','acceptance_criteria_justified')


def eligibility(checks):
    unknown=set(checks)-set(REQUIRED)
    if unknown:raise ValueError('Unknown eligibility prerequisites')
    failures=[k for k in REQUIRED if checks.get(k) is not True]
    return dict(eligible=not failures,unmet_prerequisites=failures)


def require_executable(protocol):
    if protocol.get('status')!='FROZEN_FOR_EXECUTION':raise ValueError('Final protocol is not frozen for execution')
    models=protocol.get('models',[])
    if not models or any(not eligibility(m['checks'])['eligible'] for m in models):raise ValueError('No fully eligible evaluation set')
    for model in models:
        if not model.get('checkpoint') or not model.get('cohort') or not model.get('acceptance_criteria'):
            raise ValueError('Checkpoint, cohort and acceptance criteria must be bound before execution')
    return models
