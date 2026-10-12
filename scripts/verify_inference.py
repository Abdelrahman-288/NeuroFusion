"""Compare label-free inference with previously saved development predictions."""
import json
from pathlib import Path
import numpy as np
import nibabel as nib
from neurofusion.inference import Predictor
from neurofusion.tumor_segmentation import native_probability
from neurofusion.data import save_json

project=Path(__file__).resolve().parents[1]
output=project/'experiments/inference-integration-002'
if output.exists(): raise ValueError('Verification already exists')
predictor=Predictor(project)
tumor_cases=json.loads((project/'experiments/tumor-seg-001/validation.json').read_text())
case=tumor_cases[len(tumor_cases)//2]
path=project/'data/raw/brisc-v6/brisc2025'/case['path']
r=predictor.analyze(path,'tumor-image',output/'tumor')
classification=next(c for c in json.loads((project/'experiments/tumor-cnn-002/validation-predictions.json').read_text()) if c['path']==case['path'])
delta=max(abs(r['classification']['scores'][name]-value) for name,value in zip(['glioma','meningioma','pituitary','no_tumor'],classification['probabilities']))
with np.load(project/'experiments/tumor-seg-001/predictions'/case['prediction']) as saved:
    with np.load(output/'tumor/probability.npz') as actual:
        seg_delta=float(np.max(np.abs(native_probability(saved['probability'],actual['probability'].shape)-actual['probability'])))
manifest=json.loads((project/'experiments/isles-curated-001/manifest.json').read_text())
prior=json.loads((project/'experiments/dwi-component-001/summary.json').read_text())['final_validation']['cases'][0]
study=next(s for s in manifest['studies'] if s['subject_id']==prior['subject'])
dwi=Path(manifest['data_root'])/study['files']['dwi']['path']
s=predictor.analyze(dwi,'stroke-dwi',output/'stroke')
a=nib.load(output/'stroke/probability.nii.gz')
b=nib.load(project/'experiments/dwi-component-001/predictions'/f'{prior["subject"]}-probability.nii.gz')
stroke_delta=float(np.max(np.abs(a.get_fdata()-b.get_fdata())))
result={'tumor_classification_max_difference':delta,'tumor_segmentation_max_difference':seg_delta,
        'stroke_probability_max_difference':stroke_delta,'stroke_affine_matches':bool(np.allclose(a.affine,b.affine)),
        'tumor_validation_path':case['path'],'stroke_validation_subject':prior['subject'],
        'tolerance':1e-4,'passed':delta<1e-4 and seg_delta<1e-4 and stroke_delta<1e-4 and np.allclose(a.affine,b.affine)}
save_json(output/'verification.json',result)
print(json.dumps(result,indent=2))
if not result['passed']: raise SystemExit(1)
