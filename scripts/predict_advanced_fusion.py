"""Experimental label-free fusion inference; no active model registration."""
import argparse
import json
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
from pathlib import Path
import numpy as np
import torch
from neurofusion.advanced_fusion import SeparateEncoderUNet,modality_input,ensemble_probabilities,entropy,inference_members
from neurofusion.fusion_inputs import prepare_inputs
from neurofusion.segmentation import CompactUNet,predict_volume
from neurofusion.preprocessing import restore_prediction
from neurofusion.cohort import digest
from neurofusion.data import save_json

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dwi',type=Path);parser.add_argument('--adc',type=Path)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--experimental-ensemble',action='store_true',help='Explicitly run the underperforming research ensemble; default retains DWI baseline')
args=parser.parse_args()
if args.output.exists():parser.error('Fresh output required')
if args.dwi is None:parser.error('DWI is required: the evaluated ADC-only fallback failed on all development cases and is disabled')
root=Path(__file__).resolve().parents[1]
report=json.loads((root/'experiments/advanced-fusion-001/summary.json').read_text())
arrays,meta=prepare_inputs(args.dwi,args.adc)
torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
device='cuda' if torch.cuda.is_available() else 'cpu'
names=inference_members(has_dwi='dwi' in arrays,has_adc='adc' in arrays,experimental=args.experimental_ensemble)
probabilities=[]
for name in names:
    path=root/'experiments'/name/'last.pt'
    if digest(path)!=report['checkpoint_sha256'][name]:raise ValueError('Evaluated checkpoint changed')
    with torch.serialization.safe_globals([np._core.multiarray.scalar,np.dtype,type(np.dtype('float64'))]):
        checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    model=SeparateEncoderUNet() if name=='separate-encoder-001' else CompactUNet(2 if name=='dwi-adc-002' else 1)
    model.load_state_dict(checkpoint['model']);model=model.to(device).eval()
    inputs=modality_input(arrays.get('dwi'),arrays.get('adc')) if name=='separate-encoder-001' else np.stack([arrays['dwi'],arrays['adc']]) if name=='dwi-adc-002' else arrays['dwi']
    probabilities.append(predict_volume(model,inputs,device))
    del model
mean,variance=ensemble_probabilities(probabilities)
restore_prediction(mean,meta,args.output/'probability.nii.gz')
restore_prediction(entropy(mean).astype(np.float32),meta,args.output/'entropy.nii.gz')
if len(names)>1:restore_prediction(variance,meta,args.output/'disagreement.nii.gz')
save_json(args.output/'result.json',{'research_only':True,'models':{n:report['checkpoint_sha256'][n] for n in names},
    'selection_policy':'explicit experimental ensemble' if args.experimental_ensemble else 'DWI baseline retained because fusion has not passed qualification',
    'adc_used_for_prediction':args.experimental_ensemble and 'adc' in arrays,
    'available_modalities':list(arrays),'input_sha256':{k:digest(p) for k,p in [('dwi',args.dwi),('adc',args.adc)] if p is not None},
    'transform':meta,'calibration_applied':False,'abstention_decision':None,'independent_reliability_established':False,
    'limitations':'Experimental probabilities and uncertainty maps only. Simulated missing-input development evidence; standalone ADC applicability not established. No clinical interpretation or reliable correctness probability.'})
print('Saved experimental fusion outputs; no reliability or clinical claim')
