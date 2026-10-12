"""Verify that the assembled real candidate cannot change the active registry."""
import json
from pathlib import Path
from neurofusion.inference import MODELS
from neurofusion.model_registry import active_models,read_registry,promote
from neurofusion.cohort import digest

root=Path(__file__).resolve().parents[1]
folder=root/'experiments/versioned-retraining-acceptance-001'
report=folder/'promotion.json';decision=json.loads((folder/'decision.json').read_text())
if decision['eligible'] is not False:raise ValueError('This verification is for the rejected candidate only')
before=read_registry(root,MODELS);active=active_models(root,MODELS)
expected=before['revisions'][-1]['number'] if before['revisions'] else -1
try:
    promote(root,MODELS,report.relative_to(root).as_posix(),expected)
except ValueError as error:
    reason=str(error)
else:raise AssertionError('Rejected candidate unexpectedly promoted')
assert read_registry(root,MODELS)==before and active_models(root,MODELS)==active
result=dict(passed=True,rejection_reason=reason,failed_or_missing=decision['failed_or_missing'],
            report_sha256=digest(report),active_registry_unchanged=True,protected_data_used=False)
with (folder/'rejection-verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
