"""Download the pinned public BRISC release, preserve metadata and safely extract."""
from neurofusion.download_policy import require_dataset_download
require_dataset_download()
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import datetime,timezone

root=Path('data/downloads/brisc-v6')
target=Path('data/raw/brisc-v6').resolve()
root.mkdir(parents=True,exist_ok=True)
metadata_url='https://www.kaggle.com/api/v1/datasets/view/briscdataset/brisc2025'
with urllib.request.urlopen(metadata_url,timeout=60) as response:
    metadata=json.load(response)
if metadata['currentVersionNumber']!=6:
    raise RuntimeError('Review changed release before downloading')
(root/'kaggle-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
archive=root/'brisc-v6.zip'
url='https://www.kaggle.com/api/v1/datasets/download/briscdataset/brisc2025?datasetVersionNumber=6'
if not archive.exists():
    subprocess.run(['curl.exe','-L','--fail','--retry','3','--connect-timeout','20',
                    '--max-time','600','--output',str(root/'download.part'),url],check=True)
    (root/'download.part').rename(archive)
checksum=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
with zipfile.ZipFile(archive) as bundle:
    for item in bundle.infolist():
        destination=(target/item.filename).resolve()
        if not destination.is_relative_to(target) or (item.external_attr>>16)&0o170000==0o120000:
            raise ValueError('Unsafe archive member')
    bad=bundle.testzip()
    if bad:
        raise ValueError(f'Archive CRC failed: {bad}')
    if target.exists():
        raise ValueError('Extraction target already exists')
    bundle.extractall(target)
provenance={'source':url,'metadata_source':metadata_url,'version':6,'retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'bytes':archive.stat().st_size,'archive_sha256':checksum,'zip_crc_passed':True,
    'license':metadata.get('licenseName',metadata.get('licenseNameNullable')),
    'note':'Archive SHA256 is locally computed, not a publisher-provided archive checksum.'}
(root/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print(json.dumps(provenance,indent=2))
