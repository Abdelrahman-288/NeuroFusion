"""Reproduce final validation predictions from trained candidate checkpoints."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse
import json
from pathlib import Path
import nibabel as nib
import numpy as np
import torch
from neurofusion.data import save_json
from neurofusion.cohort import StudyStore,digest
from neurofusion.segmentation import CompactUNet,predict_volume
from neurofusion.tumor_segmentation import TumorUNet,load_segmentation

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--task',choices=['tumor','stroke'],required=True)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args();out=args.run/'checkpoint-reproduction.json'
if out.exists():raise ValueError('Reproduction snapshot exists')
torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
run=args.run;config=json.loads((run/'config.json').read_text());checks=[]
with torch.serialization.safe_globals([np._core.multiarray.scalar,np.dtype,type(np.dtype('float64'))]):
    state=torch.load(run/'last.pt',weights_only=True,map_location='cpu')
assert state['epoch']==10
if args.task=='tumor':
    model=TumorUNet().cuda();model.load_state_dict(state['model']);model.eval()
    x,_,_,rows=load_segmentation(config['root'],config['splits'],'validation',keep_native=False)
    saved=json.loads((run/'validation.json').read_text());assert len(rows)==len(saved)
    with torch.inference_mode():
        for start in range(0,len(rows),16):
            probs=model(torch.from_numpy(x[start:start+16]).cuda().float()/255).sigmoid()[:,0].cpu().numpy()
            for offset,p in enumerate(probs):
                i=start+offset;case=saved[i];assert rows[i]['path']==case['path']
                path=run/'predictions'/case['prediction'];assert digest(path)==case['prediction_sha256']
                with np.load(path,allow_pickle=False) as z:previous=z['probability']
                difference=float(np.max(np.abs(previous-p)))
                if difference>1e-6 or not np.array_equal(previous>=.5,p>=.5):raise ValueError('Prediction reproduction differs')
                checks.append({'case':case['path'],'max_probability_difference':difference,'threshold_mask_identical':True})
else:
    store=StudyStore(Path('experiments/isles-curated-001/manifest.json'),Path('experiments/isles-curated-001/frozen-splits-v1.json'),Path('data/preprocessing-cache'))
    assert digest(store.manifest_path)==config['manifest_sha256'] and digest(store.splits_path)==config['splits_sha256']
    model=CompactUNet().cuda();model.load_state_dict(state['model']);model.eval()
    for study in store.studies('validation'):
        x,_,meta=store.load(study);prob=predict_volume(model,x,'cuda',patch=32,overlap=.5)
        path=run/'predictions'/f'{study["subject_id"]}-probability.nii.gz'
        image=nib.as_closest_canonical(nib.load(path));previous=image.get_fdata(dtype=np.float32)
        assert np.allclose(image.affine,meta['canonical_affine'],atol=1e-4,rtol=0)
        difference=float(np.max(np.abs(previous-prob)))
        if difference>1e-6 or not np.array_equal(previous>=.5,prob>=.5):raise ValueError('Prediction reproduction differs')
        checks.append({'case':study['subject_id'],'max_probability_difference':difference,'threshold_mask_identical':True,'prediction_sha256':digest(path)})
        print(study['subject_id'],flush=True)
save_json(out,{'passed':True,'cases':checks,'case_count':len(checks),'checkpoint_sha256':digest(run/'last.pt'),
              'epoch':10,'holdout_loaded':False,'script_sha256':digest(Path(__file__))})
print(json.dumps({'passed':True,'cases':len(checks)}))
