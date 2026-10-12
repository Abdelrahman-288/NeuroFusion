"""Compare resumed and uninterrupted local checkpoints, including optimizer/RNG state."""
import argparse
import json
from pathlib import Path
import torch
from neurofusion.data import save_json


def same(a,b):
    if isinstance(a,torch.Tensor):
        return isinstance(b,torch.Tensor) and torch.equal(a,b)
    if isinstance(a,dict):
        return isinstance(b,dict) and a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):
        return type(a)==type(b) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--resumed',type=Path,required=True)
parser.add_argument('--control',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():
    parser.error('Output exists')
a=torch.load(args.resumed,weights_only=True,map_location='cpu')
b=torch.load(args.control,weights_only=True,map_location='cpu')
position='epoch' if 'epoch' in a and 'epoch' in b else 'step'
checks={key:same(a[key],b[key]) for key in ['model','optimizer','scaler','numpy_rng','torch_rng','cuda_rng','history','validations',position,'config']}
report={'passed':all(checks.values()),'checks':checks,position:a[position],
        'scope':'Exact checkpoint equality for this hardware/software run; not a cross-device determinism guarantee'}
save_json(args.output,report)
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
