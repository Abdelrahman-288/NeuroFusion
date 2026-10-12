"""Research-delivery acceptance, explicitly independent of scientific qualification."""
from pathlib import Path
from neurofusion.cohort import digest


def accept_delivery(root, requirements, dispositions, checks, artifacts):
    root=Path(root).resolve()
    required={'regression_tests','installed_package','private_recovery','promotion_rejection','evaluation_disposition'}
    if set(checks)!=required or any(v is not True for v in checks.values()):
        raise ValueError('All research delivery checks must pass')
    ids=[r['id'] for r in requirements]
    if len(ids)!=len(set(ids)) or set(dispositions)!=set(ids) or not ids:
        raise ValueError('Every retained requirement needs exactly one disposition')
    for key,value in dispositions.items():
        if value.get('outcome') not in ('delivered','delivered_with_limitations') or not value.get('explanation'):
            raise ValueError('Missing delivery outcome or explanation')
    if not artifacts:raise ValueError('Bound evidence required')
    for item in artifacts:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path)!=item['sha256']:
            raise ValueError('Missing, changed or external release evidence')
    return dict(schema_version=1,definition='Completed local research application and documented experiment outcomes',
                research_application_complete=True,delivery_percent=100,clinical_ready=False,
                all_models_qualified=False,independent_evaluation_complete=False,
                checks=checks,requirements=dispositions,evidence=artifacts,
                limitations='Local Windows environment only; no clean-machine, off-device recovery, public hosting or clinical certification claim')
