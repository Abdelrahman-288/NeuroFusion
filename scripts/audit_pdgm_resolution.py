"""Audit the acquired development case; never runs a model or selects a checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.external_adapter import prepare_pair
from neurofusion.resolution_audit import compare_masks, restore_categorical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--mask', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    native = nib.as_closest_canonical(nib.load(args.mask)).get_fdata().astype(np.uint16)
    result = {'purpose': 'annotation resolution QA, not model performance',
              'model_inference_performed': False, 'evaluation_ready': False,
              'label_semantics_verified': False, 'component_connectivity': 26,
              'source_sha256': {k: hashlib.sha256(p.read_bytes()).hexdigest()
                  for k,p in [('image',args.image),('mask',args.mask)]}, 'sizes': []}
    for size in (128,240,256):
        _, masks, meta = prepare_pair(args.image,args.mask,allowed_labels=[0,1,2,4],size=size)
        row = {'size':size, 'lost_label_slices':meta['lost_label_slices'],
               'labels':compare_masks(native,restore_categorical(masks,meta))}
        result['sizes'].append(row)
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
