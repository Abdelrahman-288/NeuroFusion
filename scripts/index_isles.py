import argparse
from pathlib import Path
from neurofusion.isles import index_isles

parser = argparse.ArgumentParser(description='Index extracted ISLES BIDS-style files')
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args = parser.parse_args()
print({'studies':index_isles(args.root,args.output),'index':str(args.output)})
