"""Connected annotation-region diagnostics, not clinical lesion detection."""
import numpy as np
from scipy.ndimage import label


def component_errors(prediction, reference):
    p=np.asarray(prediction);r=np.asarray(reference)
    if p.shape!=r.shape or p.ndim!=3 or not np.isin(p,[0,1]).all() or not np.isin(r,[0,1]).all():
        raise ValueError('Matching 3D binary masks required')
    p=p.astype(bool);r=r.astype(bool)
    def describe(mask,other):
        components,n=label(mask,structure=np.ones((3,3,3),dtype=np.uint8))
        counts=np.bincount(components.ravel(),minlength=n+1)
        overlaps=np.bincount(components[other],minlength=n+1)
        return [{'id':i,'voxels':int(counts[i]),'overlap_voxels':int(overlaps[i]),
                 'overlap_fraction':float(overlaps[i]/counts[i])} for i in range(1,n+1)]
    refs=describe(r,p);preds=describe(p,r)
    return {'connectivity':26,'matching_rule':'at least one overlapping voxel; not a clinical detection criterion',
        'reference_components':refs,'prediction_components':preds,
        'reference_components_without_overlap':sum(c['overlap_voxels']==0 for c in refs),
        'prediction_components_without_overlap':sum(c['overlap_voxels']==0 for c in preds),
        'false_negative_voxels':int((r&~p).sum()),'false_positive_voxels':int((p&~r).sum()),
        'reference_positive_slices':int(r.any(axis=(0,1)).sum()),
        'reference_empty_slices':int((~r.any(axis=(0,1))).sum()),
        'false_positive_voxels_on_reference_empty_slices':int(p[:,:,~r.any(axis=(0,1))].sum())}
