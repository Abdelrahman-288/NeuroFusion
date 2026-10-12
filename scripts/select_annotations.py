"""Build a development annotation queue from explicit patient-level scores."""
import argparse
import json
from pathlib import Path
from neurofusion.active_learning import select_annotations
from neurofusion.data import save_json
from neurofusion.external_import import digest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates',type=Path,required=True)
    parser.add_argument('--protected',type=Path,required=True)
    parser.add_argument('--budget',type=int,required=True)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Fresh output directory required')
    candidate=json.loads(args.candidates.read_text(encoding='utf-8'))
    protected=json.loads(args.protected.read_text(encoding='utf-8'))
    result=select_annotations(candidate['records'],protected_patients=protected['patient_ids'],budget=args.budget,seed=args.seed)
    args.output.mkdir(parents=True)
    save_json(args.output/'selection.json',result)
    save_json(args.output/'provenance.json',{'candidates_sha256':digest(args.candidates),'protected_sha256':digest(args.protected),
        'source_sha256':digest(Path(__file__).resolve().parents[1]/'src/neurofusion/active_learning.py')})
    print(json.dumps({'selected':len(result['selected']),'benchmark_completed':False,'training_export_permitted':False}))
