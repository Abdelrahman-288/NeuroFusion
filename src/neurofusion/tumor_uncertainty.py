"""Development-only calibration and selective-risk summaries."""
import numpy as np
from neurofusion.calibration import scale


def binary_scale(p, temperature):
    p=np.asarray(p,dtype=np.float64)
    shape=p.shape
    return scale(np.stack([1-p.ravel(),p.ravel()],1),temperature)[:,1].reshape(shape)


def binary_scores(p,y):
    p=np.asarray(p,dtype=np.float64);y=np.asarray(y)
    if p.shape!=y.shape or not p.size or not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Finite binary probabilities and labels required')
    p=p.ravel();y=y.ravel();q=np.clip(p,1e-12,1-1e-12)
    bins=np.minimum((p*10).astype(int),9)
    ece=sum(float((bins==i).mean()*abs(p[bins==i].mean()-y[bins==i].mean())) for i in range(10) if (bins==i).any())
    return dict(nll=float(-(y*np.log(q)+(1-y)*np.log1p(-q)).mean()),
                brier=float(((p-y)**2).mean()),ece=ece)


def selective_summary(fit_uncertainty, uncertainty, loss):
    fit=np.asarray(fit_uncertainty,dtype=float);u=np.asarray(uncertainty,dtype=float);loss=np.asarray(loss,dtype=float)
    if not fit.size or not u.size or u.shape!=loss.shape or not all(np.isfinite(a).all() for a in (fit,u,loss)):
        raise ValueError('Nonempty finite fitting and evaluation arrays required')
    threshold=float(np.quantile(fit,.8))
    accepted=u<=threshold
    risk=float(loss[accepted].mean()) if accepted.any() else None
    overall=float(loss.mean())
    return dict(threshold=threshold,coverage=float(accepted.mean()),accepted=int(accepted.sum()),
                overall_risk=overall,accepted_risk=risk,
                passed=bool(accepted.mean()>=.5 and risk is not None and risk<=overall))
