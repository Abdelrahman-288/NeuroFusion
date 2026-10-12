"""Replay aggregate comparisons, source hashes and patient-level regression sets."""
import json
from pathlib import Path
import numpy as np
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.model_quality import compare_stroke
from evaluate_lesions import totals

root=Path(__file__).resolve().parents[1];run=root/'experiments/stroke-zero-overlap-001'
read=lambda p:json.loads(p.read_text())
summary=read(run/'summary.json');cases=read(run/'cases.json');protocol=read(run/'protocol.json')
if digest(run/'protocol.json')!=summary['protocol_sha256']:raise ValueError('Protocol changed')
for source in read(run/'source-hashes.json'):
    if digest(root/source['path'])!=source['sha256']:raise ValueError('Probability source changed')
historical=read(root/'experiments/stroke-threshold-001/summary.json')
old=next(r for r in historical['results'] if r['threshold']==.65)
for role in ('baseline','candidate'):
    for key,value in old[role].items():
        if not np.isclose(summary['results']['selected'][role][key],value,rtol=1e-10,atol=1e-10):raise ValueError('Original threshold metrics not reproduced')
base=cases['voxel']['baseline'];base_zero={r['subject'] for r in base if r['dice']==0}
for arm in ('selected','correction'):
    actual=summary['results'][arm]
    replay=compare_stroke(base,cases['voxel'][arm],totals(cases['lesion']['baseline']),totals(cases['lesion'][arm]))
    for key,value in replay['candidate'].items():
        if not np.isclose(actual['candidate'][key],value):raise ValueError('Aggregate mismatch')
    zero={r['subject'] for r in cases['voxel'][arm] if r['dice']==0}
    if actual['newly_zero_dice_patients']!=sorted(zero-base_zero):raise ValueError('Patient regression set differs')
    if actual['expanded_checks_passed']!=all(actual['checks'].values()):raise ValueError('Acceptance decision differs')
out=run/'verification.json'
if out.exists():raise ValueError('Fresh verification required')
save_json(out,dict(passed=True,probability_files_checked=74,original_065_metrics_reproduced=True,
    comparisons_replayed=2,patient_regression_sets_verified=True,
    summary_sha256=digest(run/'summary.json'),independent_confirmation=False,promotion_permitted=False))
print(out.read_text())
