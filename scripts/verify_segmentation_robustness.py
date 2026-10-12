"""Replay all stress-test metrics from hashed predictions and original labels."""
import argparse,json
from pathlib import Path
import numpy as np
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.tumor_segmentation import load_segmentation,native_probability
from neurofusion.segmentation_robustness import paired_metrics,summarize_cases


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];read=lambda p:json.loads(p.read_text())
    protocol=read(a.run/'protocol.json');hashes=read(a.run/'prediction-hashes.json')
    summary=read(a.run/'summary.json');coverage=read(a.run/'coverage.json')
    if len(hashes)!=228 or not summary['testing_complete']:raise ValueError('Incomplete experiment')
    for name,sha in hashes.items():
        if Path(name).name!=name or digest(a.run/name)!=sha:raise ValueError('Prediction changed')
    for path,sha in protocol['source_hashes'].items():
        if digest(root/path)!=sha:raise ValueError('Evaluation code changed')
    for r in protocol['checkpoints'].values():
        if digest(root/r['path'])!=r['sha256']:raise ValueError('Checkpoint changed')
    config=read(root/'experiments/tumor-seg-001/config.json')
    if digest(Path(config['splits']))!=protocol['split_hashes']['tumor']:raise ValueError('Tumor split changed')
    _,_,truths,records=load_segmentation(config['root'],config['splits'],'validation')
    if records!=coverage['tumor'] or len(records)!=721:raise ValueError('Tumor coverage differs')
    clean=np.load(a.run/'tumor-clean.npz')['probabilities']
    historical=read(root/'experiments/tumor-seg-001/validation.json')
    historical={r['path']:r for r in historical};maxdiff=0.;mask_changes=0
    for i,(r,y) in enumerate(zip(records,truths)):
        h=historical[r['path']];path=root/'experiments/tumor-seg-001/predictions'/h['prediction']
        if digest(path)!=h['prediction_sha256']:raise ValueError('Historical tumor prediction changed')
        old=np.load(path)['probability'];maxdiff=max(maxdiff,float(np.max(np.abs(old-clean[i]))))
        mask_changes+=int(not np.array_equal(native_probability(old,y.shape)>=.5,native_probability(clean[i],y.shape)>=.5))
    if maxdiff>1e-4 or mask_changes:raise ValueError(f'Tumor clean reproduction differs: {maxdiff}, masks {mask_changes}')
    expected=read(a.run/'tumor-cases.json');metrics_checked=0
    for condition in protocol['tumor_conditions']:
        probs=np.load(a.run/f'tumor-{condition}.npz')['probabilities'];rows=[]
        for i,(r,y) in enumerate(zip(records,truths)):
            score=paired_metrics(native_probability(probs[i],y.shape),y,native_probability(clean[i],y.shape))
            rows.append(dict(id=r['path'],group_id=r['group_id'],**score))
        if rows!=expected[condition] or summarize_cases(rows)!=read(a.run/'tumor-summary.json')[condition]:raise ValueError('Tumor metrics do not replay')
        metrics_checked+=len(rows)
    manifest=root/'experiments/isles-curated-001/manifest.json';splits=root/'experiments/isles-curated-001/frozen-splits-v1.json'
    if digest(manifest)!=protocol['manifest_sha256'] or digest(splits)!=protocol['split_hashes']['stroke']:raise ValueError('Stroke provenance changed')
    store=StudyStore(manifest,splits,root/'data/preprocessing-cache');expected=read(a.run/'stroke-cases.json')
    if store.studies('validation')!=coverage['stroke'] or len(coverage['stroke'])!=37:raise ValueError('Stroke coverage differs')
    rows={c:[] for c in protocol['stroke_conditions']}
    for study in store.studies('validation'):
        subject=study['subject_id'];_,y,meta=store.load(study)
        unit=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))/1000
        clean=np.load(a.run/f'{subject}-clean.npz')['probability']
        for c in rows:
            prob=np.load(a.run/f'{subject}-{c}.npz')['probability']
            rows[c].append(dict(id=subject,**paired_metrics(prob,y,clean,unit)));metrics_checked+=1
    for c in rows:
        if rows[c]!=expected[c] or summarize_cases(rows[c])!=read(a.run/'stroke-summary.json')[c]:raise ValueError('Stroke metrics do not replay')
    if summary['tumor']!=read(a.run/'tumor-summary.json') or summary['stroke']!=read(a.run/'stroke-summary.json'):raise ValueError('Combined summary differs')
    result=dict(passed=True,prediction_files_verified=len(hashes),paired_metrics_replayed=metrics_checked,
        tumor_clean_max_difference=maxdiff,tumor_clean_changed_masks=mask_changes,
        stroke_clean_reproduction=read(a.run/'clean-stroke-reproduction.json'),
        independent_evaluation=False,holdout_used=False)
    save_json(a.run/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='stroke_clean_reproduction'},indent=2))


if __name__=='__main__':main()
