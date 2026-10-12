"""Fixed prospective continuation screens. No clinical qualification or promotion."""
from collections import defaultdict
import numpy as np


def paired_cases(baseline, candidate, key):
    a={r[key]:r for r in baseline};b={r[key]:r for r in candidate}
    if not a or len(a)!=len(baseline) or len(b)!=len(candidate) or a.keys()!=b.keys():
        raise ValueError('Unique identical development case sets required')
    for k in sorted(a):
        for field in ('group_id','label','reference_pixels','reference_voxels'):
            if a[k].get(field)!=b[k].get(field):raise ValueError('Case identity/target binding differs')
    return [(a[k],b[k]) for k in sorted(a)]


def mean(rows, key):
    v=np.asarray([r[key] for r in rows],dtype=float)
    if not np.isfinite(v).all():raise ValueError('Nonfinite metric')
    return float(v.mean())


def dice_delta_interval(pairs, group_key=None, seed=42):
    groups=defaultdict(list)
    for i,(a,b) in enumerate(pairs):groups[a[group_key] if group_key else i].append(b['dice']-a['dice'])
    deltas=np.asarray([np.mean(v) for _,v in sorted(groups.items())])
    rng=np.random.default_rng(seed)
    sampled=np.mean(deltas[rng.integers(0,len(deltas),(2000,len(deltas)))],axis=1)
    return {'unit':'image-similarity group' if group_key else 'patient','units':len(deltas),
        'mean_delta':float(deltas.mean()),'percentile_95_interval':np.percentile(sampled,[2.5,97.5]).tolist(),
        'bootstrap_samples':2000,'seed':seed,'interpretation':'Exploratory development uncertainty; repeated validation use and selection are not adjusted for.'}


def compare_tumor(baseline,candidate):
    pairs=paired_cases(baseline,candidate,'path')
    summaries=[]
    for rows in (baseline,candidate):
        groups=defaultdict(list)
        for r in rows:groups[r['group_id']].append(r['dice'])
        summaries.append({'mean_dice':mean(rows,'dice'),'mean_iou':mean(rows,'iou'),
            'mean_false_positive_pixels':mean(rows,'false_positive_pixels'),
            'group_weighted_dice':float(np.mean([np.mean(v) for v in groups.values()])),
            'per_class_dice':{c:mean([r for r in rows if r['label']==c],'dice') for c in sorted({r['label'] for r in rows})},
            'zero_dice_cases':sum(r['dice']==0 for r in rows)})
    a,b=summaries
    checks={'mean_dice_improves':b['mean_dice']>a['mean_dice'],
        'group_dice_improves':b['group_weighted_dice']>a['group_weighted_dice'],
        'iou_not_lower':b['mean_iou']>=a['mean_iou'],
        'false_positive_pixels_not_higher':b['mean_false_positive_pixels']<=a['mean_false_positive_pixels'],
        'no_class_drop_over_0_02':all(b['per_class_dice'][c]>=v-.02 for c,v in a['per_class_dice'].items())}
    return {'baseline':a,'candidate':b,'checks':checks,'development_screen_passed':all(checks.values()),
        'dice_delta':dice_delta_interval(pairs,'group_id'),'independently_qualified':False,'promotion_permitted':False}


def compare_stroke(baseline,candidate,base_lesions,new_lesions):
    pairs=paired_cases(baseline,candidate,'subject')
    summaries=[]
    for rows,lesions in ((baseline,base_lesions),(candidate,new_lesions)):
        summaries.append({'mean_dice':mean(rows,'dice'),'mean_absolute_volume_error_ml':mean(rows,'absolute_volume_error_ml'),
            'mean_false_positive_ml':mean(rows,'false_positive_ml'),
            'lesion_recall':lesions['lesion_recall'],'lesion_precision':lesions['lesion_precision'],
            'zero_overlap_components_per_scan':lesions['no_overlap_predicted_components']/len(rows),
            'zero_dice_cases':sum(r['dice']==0 for r in rows)})
    a,b=summaries
    if not all(np.isfinite(r[k]) for r in summaries for k in r):raise ValueError('Nonfinite/undefined metrics')
    checks={'mean_dice_improves':b['mean_dice']>a['mean_dice'],
        'volume_error_not_higher':b['mean_absolute_volume_error_ml']<=a['mean_absolute_volume_error_ml'],
        'false_positive_ml_not_higher':b['mean_false_positive_ml']<=a['mean_false_positive_ml'],
        'lesion_recall_not_lower':b['lesion_recall']>=a['lesion_recall'],
        'lesion_precision_not_lower':b['lesion_precision']>=a['lesion_precision'],
        'zero_overlap_components_not_higher':b['zero_overlap_components_per_scan']<=a['zero_overlap_components_per_scan']}
    return {'baseline':a,'candidate':b,'checks':checks,'development_screen_passed':all(checks.values()),
        'dice_delta':dice_delta_interval(pairs),'independently_qualified':False,'promotion_permitted':False}
