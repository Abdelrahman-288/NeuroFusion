"""Summarize declared sites and reference lesion volume before model fitting."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from neurofusion.data import audit, save_json

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',type=Path,required=True)
parser.add_argument('--splits',type=Path,required=True)
parser.add_argument('--centers',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():
    parser.error('Use a new output path')
manifest=json.loads(args.manifest.read_text())
splits=json.loads(args.splits.read_text())
centers=json.loads(args.centers.read_text())['centers']
if not audit(manifest,splits)['passed']:
    parser.error('Leakage audit failed')
report={}
for partition in ['train','validation','holdout']:
    studies=[s for s in manifest['studies'] if splits['assignments'][s['subject_id']]==partition]
    volumes=[s['files']['mask']['lesion_volume_ml'] for s in studies]
    known=[v for v in volumes if v is not None]
    site_counts=Counter(centers.get(s['subject_id'],'unknown') for s in studies)
    report[partition]={'patients':len(studies),'centers':dict(site_counts),
        'unknown_volume_count':len(volumes)-len(known),
        'lesion_ml_quantiles':dict(zip(['min','q25','median','q75','max'],np.percentile(known,[0,25,50,75,100]).tolist())) if known else {},
        'empty_masks':sum(s['files']['mask']['lesion_voxels']==0 for s in studies)}
report['notes']=['Descriptive split-design review only. No predictions or test performance inspected.',
                 'Mixed-site internal splits do not establish external-site generalization.',
                 'Do not tune thresholds, models or partitions based on holdout performance.']
report['manifest_sha256']=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
save_json(args.output,report)
print(json.dumps(report,indent=2))
