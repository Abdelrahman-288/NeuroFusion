"""Source-bound predicted-region measurements; no diagnosis or anatomical registration."""
from pathlib import Path
import numpy as np
import nibabel as nib
from scipy.ndimage import label,find_objects
from PIL import Image
from nibabel.orientations import io_orientation,axcodes2ornt,ornt_transform,inv_ornt_aff
from neurofusion.cohort import digest


def geometry(metadata):
    if metadata['xyzt_units'][0]!='mm':raise ValueError('Physical measurements require millimeter units')
    a=np.asarray(metadata['canonical_affine'],dtype=float);o=np.asarray(metadata['original_affine'],dtype=float)
    shape=tuple(metadata['canonical_shape']);original=tuple(metadata['original_shape'])
    for v in (a,o):
        if v.shape!=(4,4) or not np.isfinite(v).all() or not np.allclose(v[3],[0,0,0,1]) or abs(np.linalg.det(v[:3,:3]))<1e-8:
            raise ValueError('Invalid physical affine')
    if len(shape)!=3 or len(original)!=3 or any(not isinstance(n,int) or n<1 for n in shape+original):raise ValueError('Invalid geometry shape')
    forward=ornt_transform(io_orientation(o),axcodes2ornt(('R','A','S')))
    expected=o@inv_ornt_aff(forward,original)
    expected_shape=tuple(np.asarray(original)[np.argsort(forward[:,0].astype(int))])
    inverse=ornt_transform(axcodes2ornt(('R','A','S')),io_orientation(o))
    if shape!=expected_shape or not np.allclose(a,expected,rtol=0,atol=1e-4) or not np.array_equal(inverse,np.asarray(metadata['inverse_orientation'])):
        raise ValueError('Canonical/original transform inconsistent')
    return a,o,abs(float(np.linalg.det(a[:3,:3])))


def measure_regions(probability,metadata=None):
    p=np.asarray(probability)
    if p.ndim not in (2,3) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probability map')
    physical=p.ndim==3
    if physical:
        if metadata is None or tuple(metadata['canonical_shape'])!=p.shape:raise ValueError('Missing or mismatched geometry')
        affine,original,voxel_mm3=geometry(metadata)
    elif metadata is not None:raise ValueError('2D image has no trusted physical geometry')
    mask=p>=.5
    labeled,n=label(mask,structure=np.ones((3,)*p.ndim,dtype=np.uint8))
    findings=[]
    for component,box in enumerate(find_objects(labeled),1):
        if box is None:continue
        points=np.argwhere(labeled[box]==component)+np.array([s.start for s in box])
        center=points.mean(0);count=len(points)
        if physical:
            z=int(np.argmax(np.bincount(points[:,2],minlength=p.shape[2])))
            plane=points[points[:,2]==z]
            anchor=plane[np.argmin(((plane-center)**2).sum(1))]
            xyz=nib.affines.apply_affine(affine,center)
            native=nib.affines.apply_affine(np.linalg.inv(original),xyz)
            row=int(p.shape[1]-1-anchor[1]);col=int(anchor[0])
        else:
            z=0;anchor=points[np.argmin(((points-center)**2).sum(1))];row,col=map(int,anchor)
        r=dict(id=f'region-{component:04d}',count=count,bounds_index_inclusive=[points.min(0).tolist(),points.max(0).tolist()],
            centroid_index=center.tolist(),slice_index=z,preview_pixel_rc=[row,col],anchor_index=anchor.tolist())
        if physical:r.update(volume_ml=count*voxel_mm3/1000,centroid_ras_mm=xyz.tolist(),centroid_original_index=native.tolist())
        findings.append(r)
    findings.sort(key=lambda r:(-r['count'],r['id']))
    return dict(schema_version=1,threshold=.5,connectivity=26 if physical else 8,
        index_convention='zero-based voxel centers; canonical i,j,k; preview row=Y-1-j, column=i' if physical else 'zero-based original-image row,column',
        physical_measurements_available=physical,count=int(mask.sum()),count_unit='voxels' if physical else 'pixels',
        voxel_volume_mm3=voxel_mm3 if physical else None,total_volume_ml=int(mask.sum())*voxel_mm3/1000 if physical else None,
        coordinate_system='NIfTI RAS+ world millimeters, not atlas coordinates' if physical else 'image pixels only',
        scope='Connected components of the thresholded prediction, not confirmed lesions; no diameter or disease-severity claim',findings=findings)


def bind_evidence(measurements,result,folder):
    folder=Path(folder);m=measurements
    m['input_sha256']=result['input_sha256'];m['models']=dict(result['models'])
    m['probability_sha256']=digest(folder/result['probability_file'])
    for r in m['findings']:
        v=result['views'][r['slice_index']]
        r['evidence']={key:dict(file=v[key],sha256=digest(folder/v[key])) for key in ('image','overlay')}
    return m


def validate_evidence(result,folder):
    """Recompute measurements and reject stale, altered or mislinked saved evidence."""
    folder=Path(folder).resolve();m=result['measurements']
    def asset(name):
        path=(folder/name).resolve()
        if path.parent!=folder:raise ValueError('Evidence path escapes result directory')
        return path
    path=asset(result['probability_file'])
    if digest(path)!=m['probability_sha256'] or result['input_sha256']!=m['input_sha256'] or result['models']!=m['models']:
        raise ValueError('Measurement provenance mismatch')
    if result['task']=='stroke-dwi':
        image=nib.load(path);meta=result['native_geometry']
        if image.shape!=tuple(meta['original_shape']) or not np.allclose(image.affine,meta['original_affine'],rtol=0,atol=1e-4) or image.header.get_xyzt_units()[0]!='mm':raise ValueError('Saved probability geometry mismatch')
        canonical=nib.as_closest_canonical(image)
        p=canonical.get_fdata(dtype=np.float32)
        expected=measure_regions(p,meta)
    else:
        p=np.load(path,allow_pickle=False)['probability'];expected=measure_regions(p)
    for key,value in expected.items():
        if key!='findings' and m[key]!=value:raise ValueError('Measurement summary mismatch')
    if len(expected['findings'])!=len(m['findings']):raise ValueError('Finding count mismatch')
    checked={}
    for actual,wanted in zip(m['findings'],expected['findings']):
        if any(actual[k]!=v for k,v in wanted.items()):raise ValueError('Finding coordinate/measurement mismatch')
        z=actual['slice_index'];view=result['views'][z]
        for key in ('image','overlay'):
            e=actual['evidence'][key];path=asset(e['file'])
            if e['file']!=view[key] or digest(path)!=e['sha256']:raise ValueError('Finding image link mismatch')
        if z not in checked:
            with Image.open(asset(view['overlay'])) as im:overlay=np.asarray(im.convert('RGBA'))
            with Image.open(asset(view['image'])) as im:shape=(im.height,im.width)
            expected_mask=np.rot90(p[:,:,z]>=.5) if p.ndim==3 else p>=.5
            if overlay.shape[:2]!=shape or shape!=expected_mask.shape or not np.array_equal(overlay[:,:,3]>0,expected_mask):raise ValueError('Overlay geometry/content mismatch')
            checked[z]=overlay
        row,col=actual['preview_pixel_rc']
        if checked[z][row,col,3]==0:raise ValueError('Finding points outside overlay')
    return dict(passed=True,findings=len(m['findings']),linked_slices=len(checked))
