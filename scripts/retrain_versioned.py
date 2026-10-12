"""Freeze labels, retrain a supported model, or assemble its acceptance bundle."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json
from pathlib import Path
from neurofusion.annotation_versions import freeze
from neurofusion.retraining import train,assemble

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
f=subs.add_parser('freeze');f.add_argument('--model',choices=['tumor_classifier','tumor_segmenter','stroke_dwi'],required=True);f.add_argument('--output',type=Path,required=True);f.add_argument('--parent',type=Path);f.add_argument('--approved-export',type=Path)
t=subs.add_parser('train');t.add_argument('--annotations',type=Path,required=True);t.add_argument('--output',type=Path,required=True);t.add_argument('--epochs',type=int,default=1)
a=subs.add_parser('assemble');a.add_argument('--run',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--gate-evidence',type=Path,help='JSON mapping required gate names to local evidence JSON paths')
args=p.parse_args()
if args.command=='freeze':result=freeze(root,args.model,args.output,args.parent,args.approved_export)
elif args.command=='train':result=train(root,args.annotations,args.output,args.epochs)
else:result=assemble(root,args.run,args.output,json.loads(args.gate_evidence.read_text()) if args.gate_evidence else None)
print(result)
