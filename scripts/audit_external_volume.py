"""Check an explicitly supplied MRI/segmentation pair without running a model."""
import argparse
from pathlib import Path
from neurofusion.data import save_json
from neurofusion.pdgm import audit_volume_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--mask', type=Path, required=True)
    parser.add_argument('--allowed-labels', type=int, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output file')
    result = audit_volume_pair(args.image, args.mask, allowed_labels=args.allowed_labels)
    save_json(args.output, result)
    print('Geometry and numeric label checks passed; semantic review is still required.')


if __name__ == '__main__':
    main()
