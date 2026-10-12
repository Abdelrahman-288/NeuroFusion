"""Verify physical geometry on existing development predictions and fresh app outputs."""
import argparse,json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.measurements import measure_regions,validate_evidence
from neurofusion.data import save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--smoke',type=Path,required=True);a=parser.parse_args()
    root=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=False)
    manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
    store=StudyStore(manifest,splits,root/'data/preprocessing-cache');rows=[]
    hashes=json.loads((root/'experiments/segmentation-robustness-001/clean-stroke-reproduction.json').read_text())
    for study in store.studies('validation'):
        subject=study['subject_id'];_,_,meta=store.load(study)
        path=root/'experiments/dwi-component-001/predictions'/f'{subject}-probability.nii.gz'
        if digest(path)!=hashes[subject]['reference_sha256']:raise ValueError('Prediction changed')
        image=nib.load(path);original=image.get_fdata(dtype=np.float32);canonical=nib.as_closest_canonical(image).get_fdata(dtype=np.float32)
        if image.shape!=tuple(meta['original_shape']) or not np.allclose(image.affine,meta['original_affine'],rtol=0,atol=1e-4) or image.header.get_xyzt_units()[0]!='mm':raise ValueError('Prediction does not share original source geometry')
        m=measure_regions(canonical,meta)
        # Independent count/geometry calculation on the saved original grid.
        native_volume=int((original>=.5).sum())*abs(float(np.linalg.det(image.affine[:3,:3])))/1000
        if not np.isclose(native_volume,m['total_volume_ml'],rtol=0,atol=1e-8):raise ValueError('Volume not invariant under orientation')
        if sum(f['count'] for f in m['findings'])!=int((original>=.5).sum()):raise ValueError('Component counts do not conserve mask')
        max_error=0.
        for f in m['findings']:
            xyz=nib.affines.apply_affine(meta['canonical_affine'],f['anchor_index'])
            native=nib.affines.apply_affine(np.linalg.inv(image.affine),xyz)
            error=float(np.max(np.abs(native-np.round(native))));max_error=max(max_error,error)
            index=np.round(native).astype(int)
            if error>1e-5 or any(index<0) or any(index>=original.shape) or original[tuple(index)]<.5:raise ValueError('Finding anchor has no matching original-grid prediction')
            row,col=f['preview_pixel_rc']
            if np.rot90(canonical[:,:,f['slice_index']])[row,col]<.5:raise ValueError('Preview mapping misses region')
        rows.append(dict(subject=subject,prediction_sha256=digest(path),components=len(m['findings']),
            volume_ml=m['total_volume_ml'],original_volume_ml=native_volume,max_index_roundtrip_error=max_error))
        print('Verified',subject,flush=True)
    smoke={}
    for task in ('tumor','stroke'):
        folder=a.smoke/f'{task}-smoke';result=json.loads((folder/'result.json').read_text())
        smoke[task]=validate_evidence(result,folder)
    if len(rows)!=37:raise ValueError('Incomplete validation coverage')
    save_json(a.output/'cases.json',rows)
    save_json(a.output/'summary.json',dict(passed=True,validation_volumes=len(rows),components_verified=sum(r['components'] for r in rows),
        max_index_roundtrip_error=max(r['max_index_roundtrip_error'] for r in rows),fresh_inference=smoke,
        manifest_sha256=digest(manifest),split_sha256=digest(splits),holdout_used=False,
        clinical_measurement_accuracy_established=False,
        scope='Numerical volume, coordinate and evidence integrity; predicted masks are not reference anatomy',
        source_hashes={str(p.relative_to(root)):digest(p) for p in [Path(__file__),root/'src/neurofusion/measurements.py',root/'src/neurofusion/inference.py',root/'src/neurofusion/reports.py']}))
    print('Measurement and evidence verification passed')


if __name__=='__main__':main()
