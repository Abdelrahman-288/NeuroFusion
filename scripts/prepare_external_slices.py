"""Prepare a declared 3D MRI/mask pair for development; never runs inference."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

from neurofusion.data import save_json
from neurofusion.external_adapter import prepare_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--mask', type=Path, required=True)
    parser.add_argument('--allowed-labels', type=int, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    images, labels, metadata = prepare_pair(args.image, args.mask, allowed_labels=args.allowed_labels)
    args.output.mkdir(parents=True)
    np.savez_compressed(args.output/'slices.npz', images=images, numeric_labels=labels)
    save_json(args.output/'geometry.json', metadata)
    save_json(args.output/'source-hashes.json', {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__), Path('src/neurofusion/external_adapter.py'), Path('src/neurofusion/pdgm.py')]})
    # Fixed geometric midpoint chosen without consulting segmentation labels.
    z = len(images)//2
    Image.fromarray(images[z, 0]).save(args.output/'middle-slice.png')
    print(f'Prepared {len(images)} slices. Lost-label warnings: {len(metadata["lost_label_slices"])}. Evaluation remains disabled.')


if __name__ == '__main__':
    main()
