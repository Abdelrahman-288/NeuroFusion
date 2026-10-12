"""Descriptive paired seed statistics and development-only screening gates."""
import numpy as np


def statistics(values):
    x=np.asarray(values,dtype=float)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all():raise ValueError('At least two finite seed values required')
    return {'mean':float(x.mean()),'sample_std':float(x.std(ddof=1)), 'min':float(x.min()),'max':float(x.max())}


def screen(clean_accuracy,clean_f1,recall_deltas,stress_deltas,gates):
    clean=statistics(clean_accuracy); f1=statistics(clean_f1); stress=statistics(stress_deltas)
    checks={
        'mean_clean_accuracy':clean['mean']>=gates['mean_clean_accuracy_delta_pp_min'],
        'mean_clean_macro_f1':f1['mean']>=gates['mean_clean_macro_f1_delta_min'],
        'each_class_mean_clean_recall':all(statistics(v)['mean']>=gates['each_class_mean_clean_recall_delta_pp_min'] for v in recall_deltas.values()),
        'mean_perturbed_accuracy':stress['mean']>=gates['mean_perturbed_accuracy_delta_pp_min'],
        'each_seed_clean_accuracy':clean['min']>=gates['each_seed_clean_accuracy_delta_pp_min']}
    return {'checks':checks,'development_screen_passed':all(checks.values()),'automatic_promotion':False}
