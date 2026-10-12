"""Prespecified bounded recalibration experiment on existing development predictions."""
import argparse
import json
from pathlib import Path
import numpy as np
from neurofusion.calibration import metrics
from neurofusion.conservative_calibration import select,transform,TEMPERATURES,MIXING
from neurofusion.tumor_uncertainty import selective_summary
from neurofusion.cohort import digest
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=False)
source=root/'experiments/tumor-qualification-001'
save_json(args.output/'protocol.json',dict(method='Bounded temperature plus uniform mixing; identity fallback',
    temperatures=TEMPERATURES,mixing=MIXING,selection='Candidate must not worsen NLL or Brier in any of five fitting-group folds; minimize unweighted fold mean of NLL+Brier among eligible candidates',
    data_sha256=digest(source/'classifier-evaluation.npz'),partitions_sha256=digest(source/'classifier-partitions.json'),
    source_sha256=digest(root/'src/neurofusion/conservative_calibration.py'),
    outer_checks=['NLL not worse','Brier not worse','ECE <=0.05','retained risk no worse at fit-only 80th percentile and coverage >=0.5'],
    independent=False,limitation='Outer development groups reused after observing prior temperature failure; exploratory, not independent confirmation',
    test_loaded=False,automatic_promotion=False))
with np.load(source/'classifier-evaluation.npz') as archive:
    probabilities=archive['probabilities'];labels=archive['labels'];fit=archive['fit']
rows=json.loads((source/'classifier-partitions.json').read_text())['records']
if not np.array_equal(fit,[r['role']=='fit' for r in rows]):raise ValueError('Role mismatch')
groups=np.asarray([r['group'] for r in rows])
if set(groups[fit])&set(groups[~fit]):raise ValueError('Group overlap')
selection=select(probabilities[fit],labels[fit],groups[fit].tolist())
save_json(args.output/'selection.json',selection) # freeze decision before evaluation
choice=selection['selected'];q=transform(probabilities,choice['temperature'],choice['mixing'])
before=metrics(probabilities[~fit],labels[~fit]);after=metrics(q[~fit],labels[~fit])
selective=selective_summary(1-q[fit].max(1),1-q[~fit].max(1),(q[~fit].argmax(1)!=labels[~fit]).astype(float))
checks=dict(nll_not_worse=after['nll']<=before['nll']+1e-12,
    brier_not_worse=after['brier_multiclass_sum']<=before['brier_multiclass_sum']+1e-12,
    ece_at_most_0_05=after['ece_10_equal_width']<=.05,selective_risk=selective['passed'])
result=dict(selected=choice,identity_selected=selection['identity_selected'],before=before,after=after,
    selective=selective,checks=checks,development_checks_passed=all(checks.values()),
    independent_qualification=False,model_promoted=False,test_loaded=False,
    interpretation='Identity fallback is rejection of recalibration, not proof of improved uncertainty' if selection['identity_selected'] else 'Exploratory development calibration only')
np.savez_compressed(args.output/'evaluation.npz',probabilities=q[~fit],labels=labels[~fit])
save_json(args.output/'summary.json',result)
print(json.dumps(result,indent=2))
