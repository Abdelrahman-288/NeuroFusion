"""Training-only slice balancing and fixed development comparison rules."""
import numpy as np
import torch


def foreground_weights(dataset):
    if any(not str(exam) for _,_,exam in dataset.index):
        raise ValueError('Missing exam identity')
    flags=np.asarray([bool(dataset.arrays[c][1][z].any()) for c,z,_ in dataset.index])
    positive=int(flags.sum());negative=len(flags)-positive
    if not positive or not negative:raise ValueError('Both slice groups required')
    return torch.as_tensor(np.where(flags,.5/positive,.5/negative),dtype=torch.double),flags


def compare_runs(baseline,candidate):
    def keyed(run):
        rows=run['final_epoch']['cases'];result={r['patient_id']:r for r in rows}
        if len(result)!=len(rows) or not result:raise ValueError('Unique nonempty patients required')
        return result
    b,c=keyed(baseline),keyed(candidate)
    if b.keys()!=c.keys():raise ValueError('Patient sets differ')
    rows=[]
    for patient in sorted(b):
        bm,cm=b[patient]['metrics'],c[patient]['metrics']
        for m in (bm,cm):
            if any(m[k] is None or not np.isfinite(m[k]) for k in ('dice','iou','fp','voxel_ml')):raise ValueError('Undefined metrics cannot pass')
        rows.append({'patient_id':patient,'baseline_dice':bm['dice'],'candidate_dice':cm['dice'],'dice_delta':cm['dice']-bm['dice'],
          'baseline_iou':bm['iou'],'candidate_iou':cm['iou'],'baseline_fp_ml':bm['fp']*bm['voxel_ml'],'candidate_fp_ml':cm['fp']*cm['voxel_ml']})
    means={k:float(np.mean([r[k] for r in rows])) for k in ('baseline_dice','candidate_dice','baseline_iou','candidate_iou','baseline_fp_ml','candidate_fp_ml')}
    gates={'mean_dice_increases':means['candidate_dice']>means['baseline_dice'],
           'mean_iou_not_lower':means['candidate_iou']>=means['baseline_iou'],
           'mean_false_positive_volume_not_higher':means['candidate_fp_ml']<=means['baseline_fp_ml'],
           'no_patient_dice_drop_over_005':all(r['dice_delta']>=-.05-1e-12 for r in rows)}
    return {'patients':rows,'means':means,'gates':gates,'all_passed':all(gates.values()),
            'decision':'paired-seed confirmation candidate' if all(gates.values()) else 'retain baseline; sampling candidate rejected',
            'clinical_evaluation':False,'model_promoted':False}
