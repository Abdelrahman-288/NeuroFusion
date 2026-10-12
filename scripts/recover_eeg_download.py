"""Recover the preselected EEG pilot through the official public S3 mirror."""
from neurofusion.download_policy import require_dataset_download
require_dataset_download()
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from neurofusion.cohort import digest
from neurofusion.data import save_json
root=Path(__file__).resolve().parents[1];out=root/'experiments/eeg-pilot-001';data=root/'data/raw/chbmit-pilot'
protocol=json.loads((out/'protocol.json').read_text());records=protocol['records']
def fetch(row):
    path=data/row['path'];url='https://physionet-open.s3.amazonaws.com/chbmit/1.0.0/'+quote(row['path'],safe='/')
    if path.exists():
        if digest(path)!=row['sha256']:raise ValueError('Existing checksum mismatch')
        return row
    partial=path.with_suffix('.edf.ranged-partial')
    offset=partial.stat().st_size if partial.exists() else 0;total=None
    with partial.open('ab') as handle:
        while total is None or offset<total:
            end=offset+1024*1024-1
            for attempt in range(3):
                try:
                    with urlopen(Request(url,headers={'Range':f'bytes={offset}-{end}','Cache-Control':'no-cache'}),timeout=10) as response:
                        content=response.headers.get('Content-Range','')
                        if response.status!=206 or not content.startswith(f'bytes {offset}-'):raise ValueError('Incorrect range response')
                        total=int(content.split('/')[1]);block=response.read()
                        if len(block)!=min(end+1,total)-offset:raise ValueError('Truncated range')
                    break
                except Exception as error:
                    print(f'Retry {row["path"]} offset {offset}: {type(error).__name__}: {error}',flush=True)
                    if attempt==2:raise
            handle.write(block);offset+=len(block)
            if offset%(16*1024*1024)==0:print(f'{row["path"]}: {offset}/{total} bytes',flush=True)
    if digest(partial)!=row['sha256']:raise ValueError('Publisher checksum mismatch')
    partial.replace(path);print('Verified '+row['path'],flush=True);return row
with ThreadPoolExecutor(max_workers=3) as pool:downloaded=list(pool.map(fetch,records))
save_json(out/'download-manifest.json',{'records':downloaded,'files_verified':len(downloaded),'source':protocol['source'],'license':protocol['license'],
    'transfer':'Official physionet-open S3, checked byte ranges and publisher SHA256'})
print('All 12 recordings verified')
