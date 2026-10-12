"""Verify acquired metadata and create a patient-grouped import pilot manifest."""
import argparse
import hashlib
import html
import json
from pathlib import Path

from neurofusion.data import save_json
from neurofusion.pdgm import read_metadata, metadata_summary, acquisition_pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/downloads/ucsf-pdgm-v5-metadata'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    provenance = json.loads((args.root/'provenance.json').read_text())
    if not {'metadata_v5.csv', 'metadata_glossary.csv', 'collection.html'}.issubset({r['path'] for r in provenance['files']}):
        raise ValueError('Incomplete acquisition provenance')
    for row in provenance['files']:
        path = (args.root/row['path']).resolve()
        if not path.is_relative_to(args.root.resolve()):
            raise ValueError('Unsafe provenance path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Acquired metadata changed')
    records = read_metadata(args.root/'metadata_v5.csv')
    summary = metadata_summary(records)
    args.output.mkdir(parents=True)
    save_json(args.output/'summary.json', summary)
    save_json(args.output/'patient-index.json', {'records': records})
    save_json(args.output/'acquisition-pilot.json', {
        'purpose': 'Import/geometry development only; not a frozen external evaluation cohort',
        'selection': 'First 20 baseline patients sorted by SHA256(pdgm-import-pilot-v1:patient_id), independent of labels and model outputs',
        'evaluation_ready': False,
        'records': [{**r, 't1c_path': None, 'segmentation_path': None, 'status': 'awaiting_images'}
                    for r in acquisition_pilot(records)]})
    save_json(args.output/'provenance.json', provenance)
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8">'
        '<title>UCSF-PDGM intake</title><style>body{font:18px system-ui;max-width:950px;margin:40px auto;padding:20px;background:#101827;color:#e6edf6}pre{white-space:pre-wrap}a{color:#71d6ee}</style>'
        '<h1>UCSF-PDGM metadata intake</h1><p>Official metadata downloaded. MRI volumes not yet acquired. No model scoring.</p><pre>'
        + html.escape(json.dumps(summary, indent=2)) + '</pre><p>Follow-ups share the baseline patient ID. BraTS mappings must be considered in future cohort splits.</p>'
        '<p>A deterministic 20-patient acquisition pilot is recorded for import testing, not independent evaluation.</p>'
        '<p><a href="summary.json">Summary JSON</a></p>', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
