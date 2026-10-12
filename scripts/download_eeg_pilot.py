"""Bounded official CHB-MIT pilot with publisher checksums and explicit selection."""
from neurofusion.download_policy import require_dataset_download
require_dataset_download()
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
from neurofusion.eeg import parse_summary,patient_group
from neurofusion.data import save_json
from neurofusion.cohort import digest

root=Path(__file__).resolve().parents[1];data=root/'data/raw/chbmit-pilot';out=root/'experiments/eeg-pilot-001'
if out.exists():raise ValueError('Fresh experiment required')
checks={line.split(maxsplit=1)[1]:line.split()[0] for line in (data/'SHA256SUMS.txt').read_text().splitlines()}
records=[]
for i in range(1,7):
    case=f'chb{i:02d}';summary=data/case/(case+'-summary.txt')
    if digest(summary)!=checks[f'{case}/{case}-summary.txt']:raise ValueError('Publisher annotation checksum mismatch')
    entries=parse_summary(summary.read_text())
    for positive in (False,True):
        chosen=sorted([r for r in entries if bool(r['events'])==positive],key=lambda r:r['file'])[0]
        records.append({'case':case,'patient':patient_group(case),'partition':'train' if i<=4 else 'validation',
                        'path':case+'/'+chosen['file'],'events':chosen['events'],'sha256':checks[case+'/'+chosen['file']]})
out.mkdir()
protocol={'created':'2026-10-10','source':'https://physionet.org/content/chbmit/1.0.0/','license':'Open Data Commons Attribution License v1.0',
 'citation':'Guttag, J. (2010). CHB-MIT Scalp EEG Database v1.0.0. PhysioNet. DOI:10.13026/C2K01R; Shoeb (2009).',
 'selection':'Cases chb01..chb06; first lexicographic seizure-positive and seizure-free EDF per case. Label-selected engineering pilot, not representative screening evaluation.',
 'patient_roles':{'train':['chb01','chb02','chb03','chb04'],'validation':['chb05','chb06']},'same_patient_alias':{'chb21':'chb01'},
 'training':{'seed':42,'epochs':10,'batch_size':128,'lr':.001,'window_seconds':4,'target':'any positive overlap with annotated seizure interval','threshold':.5,'architecture':'six-channel 1D CNN'},
 'preprocessing':'Required six bipolar channels; 256 Hz; causal 0.5-40 Hz Butterworth filter; decimate to 128 Hz; fixed scale 100 microvolts with clipping +/-20; no normalization fit on validation',
 'evaluation':'Final epoch only; contiguous positive windows form events; one-to-one positive overlap; false alarms per background hour and detection latency; no cross-file merging',
 'independent_evaluation':False,'promotion_permitted':False,'records':records,'publisher_checksum_file_sha256':digest(data/'SHA256SUMS.txt')}
save_json(out/'protocol.json',protocol)
def download(row):
    path=data/row['path']
    if path.exists():
        if digest(path)!=row['sha256']:raise ValueError('Existing EDF checksum mismatch')
        return row
    partial=path.with_suffix('.edf.partial')
    with urlopen('https://physionet.org/files/chbmit/1.0.0/'+row['path'],timeout=90) as response,partial.open('wb') as handle:
        while block:=response.read(1024*1024):handle.write(block)
    if digest(partial)!=row['sha256']:raise ValueError('Publisher EDF checksum mismatch')
    partial.replace(path);print('Verified '+row['path'],flush=True)
    return row
with ThreadPoolExecutor(max_workers=3) as executor:downloaded=list(executor.map(download,records))
save_json(out/'download-manifest.json',{'records':downloaded,'files_verified':len(downloaded),'source':protocol['source'],'license':protocol['license']})
print('All 12 EDF recordings verified against publisher SHA256')
