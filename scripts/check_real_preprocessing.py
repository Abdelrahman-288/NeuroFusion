"""Verify lossless mask orientation roundtrip on the first draft-training study."""
import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from neurofusion.data import audit, save_json
from neurofusion.preprocessing import prepare_dwi, restore_prediction

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',type=Path,required=True)
parser.add_argument('--splits',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
manifest=json.loads(args.manifest.read_text())
splits=json.loads(args.splits.read_text())
if not audit(manifest,splits)['passed']:
    parser.error('Manifest/split audit failed')
study=next(s for s in manifest['studies'] if splits['assignments'][s['subject_id']]=='train')
root=Path(manifest['data_root']).resolve()
paths=[(root/study['files'][m]['path']).resolve() for m in ('dwi','mask')]
if not all(p.is_relative_to(root) for p in paths):
    parser.error('Manifest path escapes dataset root')
meta=prepare_dwi(paths[0],paths[1],args.output)
if meta['dwi_sha256'] != study['files']['dwi']['sha256'] or meta['mask_sha256'] != study['files']['mask']['sha256']:
    raise ValueError('Source changed since manifest creation; rebuild manifest')
labels=nib.load(args.output/'mask.nii.gz').get_fdata()
restore_prediction(labels,meta,args.output/'reference-mask-restored.nii.gz')
restored=nib.load(args.output/'reference-mask-restored.nii.gz')
original=nib.load(paths[1])
passed=bool(np.array_equal(restored.get_fdata(),original.get_fdata()) and np.allclose(restored.affine,original.affine))
report={'subject_id':study['subject_id'],'study_id':study['study_id'],'partition':'train',
        'passed':passed,'purpose':'Supplied reference mask orientation roundtrip; not model prediction',
        'canonical_shape':meta['canonical_shape'],'original_shape':meta['original_shape']}
save_json(args.output/'roundtrip-report.json',report)
print(json.dumps(report,indent=2))
raise SystemExit(0 if passed else 1)
