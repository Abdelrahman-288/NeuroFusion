"""Explicit connected-component analysis, not an official challenge evaluator."""
import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching


def lesion_metrics(probability,reference,voxel_ml,threshold=.5,connectivity=26,min_iou=0.):
    if probability.shape!=reference.shape or probability.ndim!=3:
        raise ValueError('Matching 3D arrays required')
    if not np.isfinite(probability).all() or np.any((probability<0)|(probability>1)):
        raise ValueError('Probabilities must be finite in [0,1]')
    if not np.isin(reference,[0,1]).all():
        raise ValueError('Binary reference required')
    if not np.isfinite(voxel_ml) or voxel_ml<=0 or not 0<threshold<1 or not 0<=min_iou<=1:
        raise ValueError('Invalid scale or threshold')
    if connectivity not in (6,26):
        raise ValueError('Connectivity must be 6 or 26')
    structure=ndimage.generate_binary_structure(3,1 if connectivity==6 else 3)
    ref,nref=ndimage.label(reference>0,structure=structure)
    pred,npred=ndimage.label(probability>=threshold,structure=structure)
    ref_sizes=np.bincount(ref.ravel(),minlength=nref+1)
    pred_sizes=np.bincount(pred.ravel(),minlength=npred+1)
    overlap=(ref>0)&(pred>0)
    if overlap.any():
        pairs,counts=np.unique(np.stack([ref[overlap],pred[overlap]],axis=1),axis=0,return_counts=True)
        iou=counts/(ref_sizes[pairs[:,0]]+pred_sizes[pairs[:,1]]-counts)
        keep=iou>=min_iou
        eligible=pairs[keep]
        graph=csr_matrix((np.ones(len(eligible),dtype=np.int8),(eligible[:,0]-1,eligible[:,1]-1)),shape=(nref,npred))
    else:
        pairs=np.empty((0,2),dtype=int)
        counts=np.array([],dtype=int)
        graph=csr_matrix((nref,npred),dtype=np.int8)
    matching=maximum_bipartite_matching(graph,perm_type='column') if nref and npred else np.full(nref,-1,dtype=int)
    matched_preds={int(p)+1 for p in matching if p>=0}
    ref_overlap=np.bincount(ref[overlap],minlength=nref+1)
    pred_overlap=np.bincount(pred[overlap],minlength=npred+1)
    intersection={(int(r),int(p)):int(c) for (r,p),c in zip(pairs,counts)}
    ref_boxes=ndimage.find_objects(ref)
    pred_boxes=ndimage.find_objects(pred)
    refs=[]
    for rid in range(1,nref+1):
        pid=int(matching[rid-1])+1 if matching[rid-1]>=0 else None
        count=int(ref_sizes[rid])
        common=intersection.get((rid,pid),0)
        refs.append({'component':rid,'voxels':count,'volume_ml':count*voxel_ml,'matched_prediction':pid,
            'matched':pid is not None,'any_overlap':bool(ref_overlap[rid]),
            'reference_fraction_covered':float(ref_overlap[rid]/count),
            'matched_pair_iou':float(common/(count+pred_sizes[pid]-common)) if pid else None,
            'bbox':[[s.start,s.stop] for s in ref_boxes[rid-1]]})
    preds=[]
    for pid in range(1,npred+1):
        preds.append({'component':pid,'voxels':int(pred_sizes[pid]),'volume_ml':float(pred_sizes[pid]*voxel_ml),
            'matched':pid in matched_preds,'any_overlap':bool(pred_overlap[pid]),
            'bbox':[[s.start,s.stop] for s in pred_boxes[pid-1]]})
    tp=sum(r['matched'] for r in refs)
    return {'reference_lesions':nref,'predicted_components':npred,'matched_pairs':tp,
        'missed_reference_lesions':nref-tp,'unmatched_predicted_components':npred-tp,
        'no_overlap_predicted_components':sum(not p['any_overlap'] for p in preds),
        'lesion_recall':tp/nref if nref else None,'lesion_precision':tp/npred if npred else None,
        'lesion_f1':2*tp/(nref+npred) if nref+npred else None,
        'reference_details':refs,'prediction_details':preds}
