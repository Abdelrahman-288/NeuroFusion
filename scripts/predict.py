"""Run a registered model task without any reference labels."""
import argparse
from pathlib import Path
from neurofusion.inference import Predictor

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--task',choices=['tumor-image','stroke-dwi'],required=True)
p.add_argument('--input',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
Predictor(Path(__file__).resolve().parents[1]).analyze(args.input,args.task,args.output)
print(args.output/'result.json')
