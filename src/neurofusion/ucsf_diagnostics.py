"""Probability diagnostics at a fixed threshold; never select a new threshold."""
import numpy as np


def probability_diagnostics(probabilities, target):
    p=np.asarray(probabilities,dtype=np.float32);y=np.asarray(target)
    if p.shape!=y.shape or p.ndim!=3 or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not np.isin(y,[0,1]).all():
        raise ValueError('Matching finite 3D probabilities and binary target required')
    y=y.astype(bool);result={}
    for name,mask in [('foreground',y),('background',~y)]:
        values=p[mask];n=len(values)
        result[name]={'voxels':n,'mean_probability':float(values.mean(dtype=np.float64)) if n else None,
                      'max_probability':float(values.max()) if n else None,'voxels_ge_05':int((values>=.5).sum()),
                      'histogram_20_bins':np.histogram(values,bins=np.linspace(0,1,21))[0].tolist()}
    positive=y.any(axis=(1,2));pred=p>=.5
    result['slices']={'total':len(p),'reference_positive':int(positive.sum()),
                     'reference_positive_with_empty_prediction':int((positive&~pred.any(axis=(1,2))).sum()),
                     'reference_empty_with_prediction':int((~positive&pred.any(axis=(1,2))).sum()),
                     'fp_voxels_on_reference_empty_slices':int(pred[~positive].sum())}
    result['predicted_fraction']=float(pred.mean());result['reference_fraction']=float(y.mean())
    return result
