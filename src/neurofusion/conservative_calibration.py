"""Bounded calibration selected entirely within development fitting groups."""
import hashlib
import numpy as np
from neurofusion.calibration import validate, scale, metrics

TEMPERATURES=(.75,1.,1.25,1.5,2.)
MIXING=(0.,.01,.025,.05,.1)


def transform(p,temperature,mixing):
    p=validate(p)
    if not np.isfinite(mixing) or not 0<=mixing<1:
        raise ValueError('Mixing must be finite in [0,1)')
    if temperature==1 and mixing==0:
        return p.copy()
    return (1-mixing)*scale(p,temperature)+mixing/p.shape[1]


def select(p,y,groups):
    p=validate(p,y);y=np.asarray(y)
    if len(groups)!=len(p) or any(not isinstance(g,str) or not g for g in groups):
        raise ValueError('One nonempty group ID per image required')
    unique=sorted(set(groups),key=lambda g:hashlib.sha256(('tumor-calibration-inner-v1:'+g).encode()).hexdigest())
    if len(unique)<5:raise ValueError('At least five fitting groups required')
    folds={g:i%5 for i,g in enumerate(unique)}
    assignments=np.asarray([folds[g] for g in groups])
    baseline=[metrics(p[assignments==i],y[assignments==i]) for i in range(5)]
    rows=[]
    for temperature in TEMPERATURES:
        for mixing in MIXING:
            q=transform(p,temperature,mixing)
            scores=[metrics(q[assignments==i],y[assignments==i]) for i in range(5)]
            # A fixed candidate is eligible only if neither proper score worsens
            # in any fitting fold. Outer evaluation is unavailable to this function.
            eligible=all(s['nll']<=b['nll']+1e-12 and s['brier_multiclass_sum']<=b['brier_multiclass_sum']+1e-12 for s,b in zip(scores,baseline))
            objective=float(np.mean([s['nll']+s['brier_multiclass_sum'] for s in scores]))
            rows.append(dict(temperature=temperature,mixing=mixing,eligible=eligible,objective=objective))
    chosen=min((r for r in rows if r['eligible']),key=lambda r:(r['objective'],abs(r['temperature']-1),r['mixing']))
    return dict(selected=chosen,candidates=rows,folds=assignments.tolist(),
                identity_selected=chosen['temperature']==1 and chosen['mixing']==0)
