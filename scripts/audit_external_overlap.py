"""Audit a declared PNG/JPEG cohort against every frozen BRISC classification image."""
import argparse
import hashlib
import html
import json
from pathlib import Path

from neurofusion.data import save_json
from neurofusion.overlap import index_images, screen_overlap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', type=Path, default=Path('data/raw/brisc-v6/brisc2025'))
    parser.add_argument('--splits', type=Path, default=Path('experiments/brisc-curated-001/splits.json'))
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    split = json.loads(args.splits.read_text(encoding='utf-8'))
    if split.get('frozen') is not True:
        raise ValueError('Frozen reference partitions required')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    for field in ('dataset_id', 'source', 'license', 'purpose'):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f'Manifest requires nonempty {field}')
    print('Fingerprinting reference images (no inference)...', flush=True)
    references = index_images(args.reference_root, split['assignments'])
    candidates = index_images(args.candidate_root, manifest['images'])
    report = screen_overlap(references, candidates)
    report['dataset_id'] = manifest['dataset_id']
    report['purpose'] = manifest['purpose']
    report['reference_partitions'] = sorted({r['partition'] for r in split['assignments']})
    args.output.mkdir(parents=True)
    save_json(args.output/'summary.json', report)
    save_json(args.output/'fingerprints.json', {'reference': references, 'candidate': candidates})
    save_json(args.output/'candidate-manifest.json', manifest)
    source_paths = [args.splits, args.manifest, Path(__file__), Path('src/neurofusion/overlap.py')]
    save_json(args.output/'provenance.json', {
        'reference_root': str(args.reference_root.resolve()),
        'candidate_root': str(args.candidate_root.resolve()),
        'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
    })
    compact = {k: v for k, v in report.items() if k not in ('matches', 'dispositions')}
    (args.output/'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>NeuroFusion overlap audit</title>'
        '<style>body{font:17px system-ui;max-width:1000px;margin:40px auto;padding:20px;background:#101827;color:#e6edf6}pre{white-space:pre-wrap}a{color:#71d6ee}</style>'
        '<h1>External dataset overlap screening</h1><p>Readiness tooling — not external model evaluation.</p>'
        '<pre>'+html.escape(json.dumps(compact, indent=2))+'</pre>'
        '<p><a href="summary.json">Full match evidence</a></p>', encoding='utf-8')
    print(json.dumps(compact, indent=2))


if __name__ == '__main__':
    main()
