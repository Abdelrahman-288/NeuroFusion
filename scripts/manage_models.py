"""Inspect, promote or roll back local models; never downloads or trains."""
import argparse
import json
from pathlib import Path
from neurofusion.inference import MODELS
from neurofusion.model_registry import active_models, read_registry, promote, rollback

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
commands=parser.add_subparsers(dest='action',required=True)
commands.add_parser('status')
p=commands.add_parser('promote');p.add_argument('--report',required=True);p.add_argument('--expected-revision',type=int,required=True)
p=commands.add_parser('rollback');p.add_argument('--revision',type=int,required=True);p.add_argument('--expected-revision',type=int,required=True)
args=parser.parse_args()
if args.action=='status':
    result={'active':active_models(root,MODELS),'history':read_registry(root,MODELS)}
elif args.action=='promote':
    result=promote(root,MODELS,args.report,args.expected_revision)
else:result=rollback(root,MODELS,args.revision,args.expected_revision)
print(json.dumps(result,indent=2))
