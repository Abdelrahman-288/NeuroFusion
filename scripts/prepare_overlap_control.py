"""Create deliberate BRISC overlaps to validate the auditor, never an external cohort."""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from neurofusion.data import save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    rows = json.loads(Path('experiments/brisc-curated-001/splits.json').read_text())['assignments']
    args.output.mkdir(parents=True)
    images = []
    root = Path('data/raw/brisc-v6/brisc2025')
    for label in sorted({r['label'] for r in rows}):
        row = next(r for r in rows if r['label'] == label and r['partition'] == 'train')
        source = root/row['path']
        for variant in ('copy', 'decoded', 'resize'):
            filename = f'{label}-{variant}.' + ('jpg' if variant == 'copy' else 'png')
            path = args.output/filename
            if variant == 'copy':
                shutil.copyfile(source, path)
            else:
                with Image.open(source) as image:
                    converted = image.convert('RGB')
                    if variant == 'resize':
                        converted = converted.resize((256, 256))
                    converted.save(path)
            images.append({'path': filename, 'patient_id': f'CONTROL-{label}',
                           'source_image': row['path'], 'transformation': variant})
    # An unrelated artificial image shares a mock ID with an overlapping control.
    # It tests patient propagation, not real patient metadata or MRI performance.
    Image.fromarray(np.random.default_rng(923).integers(0, 256, (64, 64, 3), dtype=np.uint8)).save(args.output/'synthetic.png')
    images.append({'path': 'synthetic.png', 'patient_id': 'CONTROL-glioma', 'transformation': 'synthetic noise'})
    save_json(args.output/'manifest.json', {'dataset_id': 'brisc-positive-control',
        'source': 'Local BRISC training images plus synthetic noise; NOT independent data',
        'license': 'BRISC source CC-BY-4.0; transformations recorded',
        'purpose': 'Positive-control audit verification only; mock patient IDs; never train or evaluate a model on these controls',
        'images': images})


if __name__ == '__main__':
    main()
