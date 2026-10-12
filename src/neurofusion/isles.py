"""Strict BIDS-style ISLES index builder; ambiguous or missing files are errors."""
import csv
from pathlib import Path
import re


def index_isles(root: Path, output: Path) -> int:
    if output.exists():
        raise ValueError('Index output already exists')
    studies = {}
    for path in sorted(root.rglob('*.nii*')):
        if not (path.name.endswith('.nii') or path.name.endswith('.nii.gz')):
            continue
        name = path.name.removesuffix('.gz').removesuffix('.nii')
        subject = re.search(r'(?:^|_)(sub-[A-Za-z0-9]+)(?:_|$)', name)
        session = re.search(r'(?:^|_)(ses-[A-Za-z0-9]+)(?:_|$)', name)
        suffix = name.split('_')[-1].lower()
        key = {'dwi':'dwi','adc':'adc','flair':'flair','msk':'mask','mask':'mask'}.get(suffix)
        if key is None:
            continue
        if not subject or not session:
            raise ValueError(f'Missing source subject/session identity: {path.name}')
        identity = (subject.group(1), session.group(1))
        row = studies.setdefault(identity, {'subject_id':identity[0],'study_id':identity[1]})
        if key in row:
            raise ValueError(f'Ambiguous {key} files for {identity}')
        row[key] = path.relative_to(root).as_posix()
    if not studies:
        raise ValueError('No recognized ISLES studies found')
    for identity,row in studies.items():
        missing = {'dwi','adc','flair','mask'} - row.keys()
        if missing:
            raise ValueError(f'Missing {sorted(missing)} for {identity}')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',newline='',encoding='utf-8') as stream:
        writer = csv.DictWriter(stream,fieldnames=['subject_id','study_id','dwi','adc','flair','mask'])
        writer.writeheader()
        writer.writerows(studies[k] for k in sorted(studies))
    return len(studies)
