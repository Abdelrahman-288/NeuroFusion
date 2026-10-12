"""Create a frozen SYNTHETIC fixture to exercise the full runner without patient data."""
import argparse
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import build_manifest,save_json,split_patients
from neurofusion.demo import create_demo

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():
    parser.error('Use a new output directory')
index=create_demo(args.output/'raw')
manifest=build_manifest(index,args.output/'raw','synthetic-runner-integration')
mp=args.output/'manifest.json'
save_json(mp,manifest)
split=split_patients(manifest)
split.update(frozen=True,manifest_sha256=digest(mp))
save_json(args.output/'splits.json',split)
