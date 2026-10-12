"""Paired segmentation stress metrics and normalized DWI perturbations."""
import numpy as np
from scipy.ndimage import gaussian_filter
from neurofusion.segmentation import metrics

DWI_CONDITIONS=('clean','scale_080','scale_120','offset_020','noise_010','blur_100')


def perturb_dwi(values,condition,seed):
    x=np.asarray(values,dtype=np.float32)
    if x.ndim!=3 or not np.isfinite(x).all() or condition not in DWI_CONDITIONS:
        raise ValueError('Expected finite 3D normalized DWI and known condition')
    # Post-normalization stress, not a simulation of raw scanner acquisition.
    if condition=='clean': return x.copy()
    if condition=='scale_080': return x*.8
    if condition=='scale_120': return x*1.2
    if condition=='offset_020': return x+np.float32(.2)
    if condition=='noise_010': return x+np.random.default_rng(seed).normal(0,.1,x.shape).astype(np.float32)
    return gaussian_filter(x,sigma=1,mode='reflect')


def paired_metrics(probability,truth,clean,unit=1.):
    p=np.asarray(probability); c=np.asarray(clean); y=np.asarray(truth)
    if p.shape!=y.shape or c.shape!=y.shape or not np.isfinite(p).all() or not np.isfinite(c).all():
        raise ValueError('Invalid paired geometry or nonfinite scores')
    if np.any((p<0)|(p>1)) or np.any((c<0)|(c>1)) or not np.isfinite(unit) or unit<=0:
        raise ValueError('Invalid probability or physical unit')
    score=metrics(p,y,.5); base=metrics(c,y,.5)
    return dict(dice=score['dice'],dice_change=score['dice']-base['dice'],
        false_positive=score['false_positive_voxels']*unit,
        volume_error=abs(score['predicted_voxels']-score['reference_voxels'])*unit,
        zero_overlap=score['dice']==0,new_zero_overlap=score['dice']==0 and base['dice']>0,
        recovered_overlap=score['dice']>0 and base['dice']==0,
        mask_flip_fraction=float(np.mean((p>=.5)!=(c>=.5))),
        probability_mae=float(np.mean(np.abs(p-c))))


def summarize_cases(rows):
    if not rows: raise ValueError('Empty cohort')
    keys=('dice','dice_change','false_positive','volume_error','mask_flip_fraction','probability_mae')
    result={k:float(np.mean([r[k] for r in rows])) for k in keys}
    result.update(cases=len(rows),zero_overlap=sum(r['zero_overlap'] for r in rows),
        new_zero_overlap=[r['id'] for r in rows if r['new_zero_overlap']],
        recovered_overlap=[r['id'] for r in rows if r['recovered_overlap']],
        worst_dice_change=float(min(r['dice_change'] for r in rows)))
    # Descriptive fixed development flags; not clinical acceptance criteria.
    result['development_flags']={'mean_dice_drop_over_005':result['dice_change']<-.05,
        'new_zero_overlap':bool(result['new_zero_overlap'])}
    return result
