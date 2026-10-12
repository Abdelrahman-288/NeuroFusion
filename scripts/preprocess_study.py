import argparse
from pathlib import Path
from neurofusion.preprocessing import prepare_dwi

parser = argparse.ArgumentParser(description='Preprocess a DWI/mask pair on its native grid')
parser.add_argument('--dwi', type=Path, required=True)
parser.add_argument('--mask', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
print(prepare_dwi(args.dwi, args.mask, args.output))
