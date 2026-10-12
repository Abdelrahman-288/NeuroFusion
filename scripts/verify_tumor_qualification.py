"""Recompute saved uncertainty results and verify development partition separation."""
import argparse
import json
from pathlib import Path
import numpy as np
from neurofusion.calibration import scale,metrics
from neurofusion.cohort import digest
from neurofusion.data import save_json


def close(actual,expected):
    if not np.isclose(actual,expected,rtol=1e-8,atol=1e-10):
        raise ValueError(f'Recomputed metric differs: {actual} / {expected}')


def separated(path):
    rows=json.loads(path.read_text())['records']
    fit={r['group'] for r in rows if r['role']=='fit'}
    evaluation={r['group'] for r in rows if r['role']=='evaluation'}
    if not fit or not evaluation or fit&evaluation:raise ValueError('Calibration groups overlap')
    return {'fit_groups':len(fit),'evaluation_groups':len(evaluation)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    out=a.run/'verification.json'
    if out.exists():raise ValueError('Verification output already exists')
    root=Path(__file__).resolve().parents[1]
    summary=json.loads((a.run/'summary.json').read_text())
    protocol=json.loads((a.run/'protocol.json').read_text())
    if digest(root/'scripts/qualify_tumor_models.py')!=protocol['source_sha256']:raise ValueError('Runner changed')
    if digest(root/'experiments/brisc-curated-001/splits.json')!=protocol['split_sha256']:raise ValueError('Split changed')
    groups=separated(a.run/'segmentation-partitions.json')
    for result in summary['segmentation']:
        with np.load(a.run/f'seed{result["seed"]}-evaluation.npz') as data:
            partition=json.loads((a.run/'segmentation-partitions.json').read_text())['records']
            if not np.array_equal(data['fit'],[r['role']=='fit' for r in partition]):raise ValueError('Saved fitting roles differ')
            p=data['sample_probability'][~data['fit']].astype(float);y=data['truth'][~data['fit']]
            logit=np.log(np.clip(p,1e-12,1))-np.log(np.clip(1-p,1e-12,1))
            q=1/(1+np.exp(-logit/result['temperature']))
            q=np.clip(q,1e-12,1-1e-12)
            close(float(-(y*np.log(q)+(1-y)*np.log1p(-q)).mean()),result['after']['nll'])
            close(float(((q-y)**2).mean()),result['after']['brier'])
            threshold=float(np.quantile(data['uncertainty'][data['fit']],.8))
            close(threshold,result['selective']['threshold'])
            selected=data['uncertainty'][~data['fit']]<=threshold
            close(float(selected.mean()),result['selective']['coverage'])
            if selected.any():close(float((1-data['dice'][~data['fit']][selected]).mean()),result['selective']['accepted_risk'])
    separated(a.run/'classifier-partitions.json')
    with np.load(a.run/'classifier-evaluation.npz') as data:
        partition=json.loads((a.run/'classifier-partitions.json').read_text())['records']
        if not np.array_equal(data['fit'],[r['role']=='fit' for r in partition]):raise ValueError('Classifier fitting roles differ')
        result=summary['classifier']
        calibrated=scale(data['probabilities'][~data['fit']],result['temperature'])
        values=metrics(calibrated,data['labels'][~data['fit']])
        for key in ('nll','brier_multiclass_sum','ece_10_equal_width'):close(values[key],result['after'][key])
        fit_probability=scale(data['probabilities'][data['fit']],result['temperature'])
        threshold=float(np.quantile(1-fit_probability.max(1),.8))
        close(threshold,result['selective']['threshold'])
        accepted=1-calibrated.max(1)<=threshold
        close(float(accepted.mean()),result['selective']['coverage'])
        if accepted.any():
            close(float((calibrated.argmax(1)[accepted]!=data['labels'][~data['fit']][accepted]).mean()),result['selective']['accepted_risk'])
    if summary['test_loaded'] or summary['promotion_permitted'] or summary['independently_qualified']:
        raise ValueError('Unsupported qualification claim')
    save_json(out,dict(passed=True,segmentation_models_recomputed=len(summary['segmentation']),
        classifier_recomputed=True,segmentation_group_separation=groups,
        summary_sha256=digest(a.run/'summary.json'),protocol_sha256=digest(a.run/'protocol.json'),
        evidence_hashes={p.name:digest(p) for p in a.run.glob('*.npz')},
        interpretation='Numerical consistency verification; not independent patient evaluation'))
    print(out.read_text())


if __name__=='__main__':main()
