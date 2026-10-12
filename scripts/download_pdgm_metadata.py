"""Acquire official UCSF-PDGM v5 metadata; does not download MRI volumes."""
from neurofusion.download_policy import require_dataset_download
require_dataset_download()
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import urllib.request

from neurofusion.data import save_json

BASE = 'https://www.cancerimagingarchive.net/'
FILES = {
    'metadata_v5.csv': BASE+'wp-content/uploads/UCSF-PDGM-metadata_v5.csv',
    'metadata_glossary.csv': BASE+'wp-content/uploads/UCSF-PDGM-metadata_glossary.csv',
    'collection.html': BASE+'collection/ucsf-pdgm/',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/downloads/ucsf-pdgm-v5-metadata'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    args.output.mkdir(parents=True)
    records = []
    for name, url in FILES.items():
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = response.read(5_000_001)
            if len(payload) > 5_000_000:
                raise ValueError('Unexpected metadata size')
            if name == 'metadata_v5.csv' and not payload.decode('utf-8-sig').startswith('ID,Sex,'):
                raise ValueError('Unexpected metadata schema or non-CSV response')
            (args.output/name).write_bytes(payload)
            records.append({'path': name, 'url': url, 'resolved_url': response.url,
                'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    save_json(args.output/'provenance.json', {'dataset': 'UCSF-PDGM', 'version': 5,
        'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'files': records,
        'license': 'CC BY 4.0', 'source': BASE+'collection/ucsf-pdgm/',
        'publisher_checksum_available': False,
        'hash_note': 'Local acquisition hashes, not publisher-provided integrity checksums.',
        'mri_volumes_downloaded': False})
    print('Official metadata, glossary and source-page snapshot saved:', args.output)


if __name__ == '__main__':
    main()
