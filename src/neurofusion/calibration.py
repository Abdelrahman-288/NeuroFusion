"""Development temperature scaling and descriptive confidence metrics."""
import hashlib
import numpy as np
from scipy.optimize import minimize_scalar


def validate(probabilities, labels=None):
    p=np.asarray(probabilities,dtype=np.float64)
    if p.ndim!=2 or not len(p) or p.shape[1]<2 or not np.isfinite(p).all() or np.any(p<0) or np.any(p>1) or not np.allclose(p.sum(1),1,atol=1e-5):
        raise ValueError('Expected finite normalized class probabilities')
    if labels is not None:
        y=np.asarray(labels)
        if y.shape!=(len(p),) or not np.issubdtype(y.dtype,np.integer) or np.any(y<0) or np.any(y>=p.shape[1]):
            raise ValueError('Invalid class labels')
    return p


def scale(probabilities, temperature):
    p=validate(probabilities)
    if not np.isfinite(temperature) or temperature<=0:
        raise ValueError('Temperature must be finite and positive')
    logits=np.log(np.clip(p,1e-12,1))/temperature
    logits-=logits.max(1,keepdims=True)
    scores=np.exp(logits)
    return scores/scores.sum(1,keepdims=True)


def group_partition(groups):
    if not groups or any(not isinstance(g,str) or not g for g in groups):
        raise ValueError('Nonempty group IDs required')
    unique=sorted(set(groups),key=lambda g:hashlib.sha256(('calibration-v1:'+g).encode()).hexdigest())
    if len(unique)<2:raise ValueError('At least two groups required')
    fitting=set(unique[:len(unique)//2])
    return np.asarray([g in fitting for g in groups])


def fit_temperature(probabilities, labels):
    p=validate(probabilities,labels);y=np.asarray(labels)
    def objective(log_t):
        scores=scale(p,np.exp(log_t))
        return float(-np.log(np.clip(scores[np.arange(len(y)),y],1e-12,1)).mean())
    result=minimize_scalar(objective,bounds=(np.log(.05),np.log(20)),method='bounded',options={'xatol':1e-8})
    if not result.success:raise ValueError('Temperature optimization failed')
    # Include identity so fitting cannot worsen the chosen objective.
    temperature=float(np.exp(result.x)) if result.fun<objective(0) else 1.
    return temperature


def metrics(probabilities, labels, bins=10):
    p=validate(probabilities,labels);y=np.asarray(labels)
    confidence=p.max(1);correct=p.argmax(1)==y
    if type(bins)is not int or bins<1:raise ValueError('Positive bin count required')
    indices=np.minimum((confidence*bins).astype(int),bins-1)
    rows=[];ece=0.
    for index in range(bins):
        chosen=indices==index;n=int(chosen.sum())
        acc=float(correct[chosen].mean()) if n else None
        conf=float(confidence[chosen].mean()) if n else None
        if n:ece+=n/len(y)*abs(acc-conf)
        rows.append({'bin':index,'count':n,'accuracy':acc,'mean_confidence':conf})
    return {'images':len(y),'accuracy':float(correct.mean()),
        'nll':float(-np.log(np.clip(p[np.arange(len(y)),y],1e-12,1)).mean()),
        'brier_multiclass_sum':float(np.square(p-np.eye(p.shape[1])[y]).sum(1).mean()),
        'ece_10_equal_width' if bins==10 else 'ece':float(ece),'reliability_bins':rows}
