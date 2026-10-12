"""Fixed development stress tests of the active tumor and DWI segmenters."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import nibabel as nib
import torch
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.inference import Predictor
from neurofusion.tumor_segmentation import load_segmentation,native_probability
from neurofusion.segmentation import predict_volume
from neurofusion.robustness import CONDITIONS,perturb
from neurofusion.segmentation_robustness import DWI_CONDITIONS,perturb_dwi,paired_metrics,summarize_cases


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=False)
    predictor=Predictor(root);tumor=predictor.model('tumor_segmenter');stroke=predictor.model('stroke_dwi')
    torch.use_deterministic_algorithms(True)
    config=json.loads((root/'experiments/tumor-seg-001/config.json').read_text())
    split=Path(config['splits'])
    if digest(split)!=config['split_sha256']:raise ValueError('Tumor split changed')
    manifest=root/'experiments/isles-curated-001/manifest.json'
    stroke_split=root/'experiments/isles-curated-001/frozen-splits-v1.json'
    store=StudyStore(manifest,stroke_split,root/'data/preprocessing-cache')
    studies=store.studies('validation');seed=20261011
    sources=[Path(__file__),root/'src/neurofusion/segmentation_robustness.py',root/'src/neurofusion/robustness.py',root/'src/neurofusion/inference.py',root/'src/neurofusion/tumor_segmentation.py',root/'src/neurofusion/segmentation.py',root/'src/neurofusion/cohort.py']
    protocol=dict(seed=seed,partition='validation',holdout_used=False,protected_ucsf_used=False,
        checkpoints={k:dict(path=v[0],sha256=v[1]) for k,v in predictor.registry.items() if k in ('tumor_segmenter','stroke_dwi')},
        threshold=.5,tumor_conditions=list(CONDITIONS),stroke_conditions=list(DWI_CONDITIONS),
        tumor_domain='128x128 normalized grayscale; original-grid scoring; positive images only',
        stroke_domain='Canonical native DWI after zscore; scale 0.8/1.2, offset +0.2 everywhere, Gaussian noise SD0.1 everywhere, Gaussian blur sigma1 voxel in 3D; no clipping or renormalization',
        selection='All existing validation cases; no tuning, training or promotion',
        flags='Descriptive development flags fixed before inference: mean Dice drop >0.05, or any new zero-overlap case; not clinical gates',
        stroke_noise_seeding='First 8 SHA256 bytes of subject ID, little endian, plus protocol seed',
        split_hashes={'tumor':digest(split),'stroke':digest(stroke_split)},manifest_sha256=digest(manifest),
        source_hashes={str(s.relative_to(root)):digest(s) for s in sources},
        device=predictor.device,torch=str(torch.__version__),numpy=np.__version__)
    save_json(a.output/'protocol.json',protocol)
    images,_,truths,records=load_segmentation(config['root'],split,'validation')
    if len(records)!=721 or len(studies)!=37:raise ValueError('Expected frozen 721 image / 37 patient coverage')
    save_json(a.output/'coverage.json',dict(tumor=records,stroke=studies))
    result={};cases={};proof={}
    clean=None
    for condition in CONDITIONS:
        x=perturb(images.astype(np.float32)/255,condition,seed);pred=[]
        with torch.inference_mode():
            for start in range(0,len(x),16):
                pred.append(tumor(torch.from_numpy(x[start:start+16]).to(predictor.device)).sigmoid()[:,0].cpu().numpy())
        pred=np.concatenate(pred)
        if condition=='clean':clean=pred.copy()
        # Save full 128x128 probabilities for exact native-grid metric replay.
        np.savez_compressed(a.output/f'tumor-{condition}.npz',probabilities=pred)
        rows=[]
        for i,(truth,row) in enumerate(zip(truths,records)):
            score=paired_metrics(native_probability(pred[i],truth.shape),truth,native_probability(clean[i],truth.shape))
            rows.append(dict(id=row['path'],group_id=row['group_id'],**score))
        cases[condition]=rows;result[condition]=summarize_cases(rows)
        print('tumor',condition,result[condition]['dice'],flush=True)
    save_json(a.output/'tumor-cases.json',cases);save_json(a.output/'tumor-summary.json',result)
    cases={c:[] for c in DWI_CONDITIONS};prediction_hashes={}
    for study in studies:
        subject=study['subject_id'];x,y,meta=store.load(study)
        unit=abs(np.linalg.det(np.asarray(meta['canonical_affine'])[:3,:3]))/1000
        case_seed=seed+int.from_bytes(hashlib.sha256(subject.encode()).digest()[:8],'little')
        clean=None
        for condition in DWI_CONDITIONS:
            prob=predict_volume(stroke,perturb_dwi(x,condition,case_seed),predictor.device)
            if condition=='clean':
                clean=prob.copy()
                old=root/'experiments/dwi-component-001/predictions'/f'{subject}-probability.nii.gz'
                # Historical predictions belong to the pinned baseline only.
                if predictor.registry['stroke_dwi'][0]=='experiments/dwi-component-001/last.pt':
                    reference=nib.as_closest_canonical(nib.load(old))
                    if reference.shape!=y.shape or not np.allclose(reference.affine,meta['canonical_affine'],atol=1e-4):raise ValueError('Reference geometry changed')
                    ref=reference.get_fdata(dtype=np.float32)
                    delta=float(np.max(np.abs(ref-prob)))
                    proof[subject]=dict(max_probability_difference=delta,mask_identical=bool(np.array_equal(ref>=.5,prob>=.5)),reference_sha256=digest(old))
                    if delta>1e-5 or not proof[subject]['mask_identical']:raise ValueError('Clean stroke reproduction failed')
            path=a.output/f'{subject}-{condition}.npz'
            np.savez_compressed(path,probability=prob)
            prediction_hashes[path.name]=digest(path)
            cases[condition].append(dict(id=subject,**paired_metrics(prob,y,clean,unit)))
        save_json(a.output/'stroke-cases.json',cases)
        print('stroke',subject,len(cases['clean']),'/37',flush=True)
    result={c:summarize_cases(r) for c,r in cases.items()}
    save_json(a.output/'stroke-summary.json',result);save_json(a.output/'clean-stroke-reproduction.json',proof)
    prediction_hashes.update({p.name:digest(p) for p in a.output.glob('tumor-*.npz')})
    save_json(a.output/'prediction-hashes.json',prediction_hashes)
    save_json(a.output/'summary.json',dict(testing_complete=True,tumor_cases=721,stroke_cases=37,
        tumor=json.loads((a.output/'tumor-summary.json').read_text()),stroke=result,
        independently_qualified=False,models_changed=False,
        limitations=['Reused development partitions; tumor image groups are not verified patients.',
        'Positive-only tumor segmentation cannot measure no-tumor specificity.',
        'Synthetic post-preprocessing intensity perturbations are not scanner/site or clinical robustness.',
        'Active checkpoints only; improved candidates and UCSF/fusion/EEG are outside this experiment.',
        'No threshold tuning, downloads, holdout evaluation or promotion.']))


if __name__=='__main__':main()
