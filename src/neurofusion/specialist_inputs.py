"""Task-specific input and target checks, not trained diagnostic specialists."""
import csv
from pathlib import Path
import numpy as np

HEMORRHAGE_LABELS=('epidural','intraparenchymal','intraventricular','subarachnoid','subdural','any')


def rsna_hemorrhage_labels(path):
    labels={}
    with Path(path).open(newline='',encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            identity,subtype=row['ID' if 'ID' in row else 'Id'].rsplit('_',1)
            value=float(row['Label'])
            if subtype not in HEMORRHAGE_LABELS or value not in (0.,1.):raise ValueError('Binary RSNA subtype targets required')
            if subtype in labels.setdefault(identity,{}):raise ValueError('Duplicate image/subtype')
            labels[identity][subtype]=int(value)
    if not labels:raise ValueError('Empty labels')
    for values in labels.values():
        if set(values)!=set(HEMORRHAGE_LABELS) or values['any']!=max(values[k] for k in HEMORRHAGE_LABELS[:-1]):raise ValueError('Incomplete or inconsistent any/subtype labels')
    return labels


def ct_windows(path):
    import pydicom
    data=pydicom.dcmread(path)
    if data.Modality!='CT' or getattr(data,'PhotometricInterpretation',None)!='MONOCHROME2':raise ValueError('Supported CT MONOCHROME2 image required')
    for name in ('PatientID','StudyInstanceUID','SeriesInstanceUID','RescaleSlope','RescaleIntercept'):
        if not getattr(data,name,None) and getattr(data,name,None)!=0:raise ValueError('Missing CT metadata: '+name)
    pixels=data.pixel_array
    if pixels.ndim!=2:raise ValueError('Single-frame CT slice required')
    slope=float(data.RescaleSlope);intercept=float(data.RescaleIntercept)
    if not np.isfinite([slope,intercept]).all() or slope==0:raise ValueError('Invalid HU transform')
    hu=pixels.astype(np.float32)*slope+intercept
    windows=np.stack([np.clip((hu-(center-width/2))/width,0,1) for center,width in [(40,80),(80,200),(600,2800)]])
    return windows,{'patient_id':str(data.PatientID),'study_id':str(data.StudyInstanceUID),'series_id':str(data.SeriesInstanceUID),
                   'input_contract':'User must verify non-contrast head CT; modality tag alone does not establish contrast or anatomy'}


def longitudinal_mask_change(baseline,followup,baseline_affine,followup_affine,*,same_patient,registration_verified,spatial_units='mm'):
    if spatial_units!='mm':raise ValueError('Explicit millimeter geometry required')
    if same_patient is not True or registration_verified is not True:raise ValueError('Verified same-patient registration required')
    a,b=np.asarray(baseline),np.asarray(followup)
    if a.ndim!=3 or a.shape!=b.shape or not np.isin(a,[0,1]).all() or not np.isin(b,[0,1]).all():raise ValueError('Matching binary 3D masks required')
    aa,bb=np.asarray(baseline_affine),np.asarray(followup_affine)
    if aa.shape!=(4,4) or bb.shape!=(4,4) or not np.isfinite(aa).all() or not np.isfinite(bb).all() or not np.allclose(aa,bb,atol=1e-4,rtol=0):raise ValueError('Common registered physical grid required')
    voxel_ml=abs(np.linalg.det(aa[:3,:3]))/1000
    if voxel_ml<=0:raise ValueError('Invalid millimeter affine')
    new=(b>0)&(a==0);resolved=(a>0)&(b==0)
    return {'baseline_volume_ml':float(a.sum()*voxel_ml),'followup_volume_ml':float(b.sum()*voxel_ml),
            'new_mask_volume_ml':float(new.sum()*voxel_ml),'resolved_mask_volume_ml':float(resolved.sum()*voxel_ml),
            'volume_change_ml':float((float(b.sum())-float(a.sum()))*voxel_ml),'interpretation':'Mask change only; not confirmed disease progression or new-lesion detection'}


def validate_vascular_targets(modality,locations_lps_mm,affine_lps,shape):
    if modality not in ('CTA','MRA'):raise ValueError('Explicit vascular acquisition contract required')
    points=np.asarray(locations_lps_mm,dtype=float)
    affine=np.asarray(affine_lps,dtype=float)
    if affine.shape!=(4,4) or not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3,:3]))<1e-8:raise ValueError('Valid LPS millimeter affine required')
    if len(shape)!=3 or any(s<=0 for s in shape):raise ValueError('Valid 3D shape required')
    if points.size==0:return []
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():raise ValueError('Finite 3D locations required')
    voxels=(np.linalg.inv(affine)@np.column_stack([points,np.ones(len(points))]).T).T[:,:3]
    if len(shape)!=3 or any(s<=0 for s in shape) or np.any(voxels<0) or np.any(voxels>np.asarray(shape)-1):raise ValueError('Target outside volume')
    return voxels.tolist()
