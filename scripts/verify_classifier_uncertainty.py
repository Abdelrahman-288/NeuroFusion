"""Replay fitting-only selection and independently recompute retained error."""
import json
from pathlib import Path
import numpy as np
from neurofusion.conservative_calibration import select,transform
from neurofusion.cohort import digest
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1]
run=root/'experiments/tumor-classifier-uncertainty-003'
source=root/'experiments/tumor-qualification-001'
protocol=json.loads((run/'protocol.json').read_text())
result=json.loads((run/'summary.json').read_text())
if digest(source/'classifier-evaluation.npz')!=protocol['data_sha256'] or digest(source/'classifier-partitions.json')!=protocol['partitions_sha256']:
    raise ValueError('Source changed')
if digest(root/'src/neurofusion/conservative_calibration.py')!=protocol['source_sha256']:raise ValueError('Calibrator changed')
with np.load(source/'classifier-evaluation.npz') as d:
    p,y,fit=d['probabilities'],d['labels'],d['fit']
rows=json.loads((source/'classifier-partitions.json').read_text())['records']
selection=select(p[fit],y[fit],[r['group'] for r,f in zip(rows,fit) if f])
if selection!=json.loads((run/'selection.json').read_text()):raise ValueError('Selection replay differs')
choice=selection['selected'];q=transform(p,choice['temperature'],choice['mixing'])
threshold=np.quantile(1-q[fit].max(1),.8);keep=1-q[~fit].max(1)<=threshold
error=(q[~fit].argmax(1)!=y[~fit])
if not np.isclose(error[keep].mean(),result['selective']['accepted_risk']):raise ValueError('Selective risk differs')
with np.load(run/'evaluation.npz') as d:
    if not np.array_equal(d['probabilities'],q[~fit]) or not np.array_equal(d['labels'],y[~fit]):raise ValueError('Saved evaluation differs')
nll=-np.log(np.clip(q[~fit][np.arange((~fit).sum()),y[~fit]],1e-12,1)).mean()
brier=((q[~fit]-np.eye(4)[y[~fit]])**2).sum(1).mean()
if not np.isclose(nll,result['after']['nll']) or not np.isclose(brier,result['after']['brier_multiclass_sum']):raise ValueError('Proper scores differ')
out=run/'verification.json'
if out.exists():raise ValueError('Verification already exists')
save_json(out,dict(passed=True,selection_replayed=True,saved_probabilities_reproduced=True,
    scores_recomputed=True,identity_fallback=selection['identity_selected'],
    summary_sha256=digest(run/'summary.json'),independently_qualified=False))
print(out.read_text())
