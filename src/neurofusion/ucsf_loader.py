"""Checked, disk-backed slices for the UCSF numeric-foreground engineering task."""
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset
from neurofusion.external_adapter import prepare_pair
from neurofusion.specialist_plan import engineering_partition


def prepare_cache(root, partitions_path, output):
    root, output = Path(root).resolve(), Path(output)
    document=json.loads(Path(partitions_path).read_text())
    rows=document['records']
    expected=engineering_partition(rows, len(document['train_patients']), document['salt'])
    if any(a['role']!=b['role'] for a,b in zip(sorted(rows,key=lambda r:r['exam_id']),expected['records'])):
        raise ValueError('Recorded roles disagree with deterministic patient assignment')
    if document['train_patients']!=expected['train_patients'] or document['development_validation_patients']!=expected['development_validation_patients']:
        raise ValueError('Patient role lists disagree')
    paths=[]
    for row in rows:
        pair=[]
        for role in ('image','mask'):
            p=(root/row[role]['path']).resolve()
            if not p.is_relative_to(root) or hashlib.sha256(p.read_bytes()).hexdigest()!=row[role]['sha256']:
                raise ValueError('Source path or checksum mismatch')
            pair.append(p)
        paths.append(pair)
    output.mkdir(parents=True,exist_ok=False)
    cases=[]
    for i,(row,pair) in enumerate(zip(rows,paths)):
        images,masks,geometry=prepare_pair(*pair,allowed_labels=[0,1,2,4],size=240)
        target=np.isin(masks,[1,2,4]).astype(np.uint8)[:,None]
        directory=output/f'case-{i:02d}';directory.mkdir()
        np.save(directory/'images.npy',images);np.save(directory/'targets.npy',target)
        (directory/'geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
        if len(images)!=row['slices'] or int(target.any(axis=(1,2,3)).sum())!=row['foreground_slices']:
            raise ValueError('Prepared slice inventory differs from recorded plan')
        for role,path in zip(('image','mask'),pair):
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row[role]['sha256']:
                raise ValueError('Source changed during preparation')
        cases.append({'exam_id':row['exam_id'],'patient_id':row['patient_id'],'role':row['role'],
            'directory':directory.name,'slices':len(images),'empty_slices':row['empty_slices'],
            'sha256':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ('images.npy','targets.npy','geometry.json')}})
        print(f'{i+1}/{len(rows)} cached',flush=True)
    result={'purpose':'engineering development only','size':240,'normalization':'adapter uint8 p1/p99 then divide by 255',
            'partitions_sha256':hashlib.sha256(Path(partitions_path).read_bytes()).hexdigest(),'cases':cases}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


class UCSFSlices(Dataset):
    def __init__(self,cache,role):
        if role not in ('train','development_validation'):
            raise ValueError('Only engineering development roles supported')
        cache=Path(cache).resolve();manifest=json.loads((cache/'manifest.json').read_text())
        patient_roles={};self.arrays=[];self.index=[]
        for row in manifest['cases']:
            if row['patient_id'] in patient_roles and patient_roles[row['patient_id']]!=row['role']:
                raise ValueError('Patient crosses roles')
            patient_roles[row['patient_id']]=row['role']
        for row in manifest['cases']:
            if row['role']!=role:continue
            directory=(cache/row['directory']).resolve()
            if not directory.is_relative_to(cache):raise ValueError('Cache path escapes root')
            for name in ('images.npy','targets.npy','geometry.json'):
                if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=row['sha256'][name]:raise ValueError('Cache checksum mismatch')
            x=np.load(directory/'images.npy',mmap_mode='r',allow_pickle=False)
            y=np.load(directory/'targets.npy',mmap_mode='r',allow_pickle=False)
            if x.shape!=(row['slices'],1,240,240) or y.shape!=x.shape or x.dtype!=np.uint8 or y.dtype!=np.uint8 or not np.isin(y,[0,1]).all():
                raise ValueError('Invalid cached arrays')
            case=len(self.arrays);self.arrays.append((x,y))
            self.index.extend((case,z,row['exam_id']) for z in range(len(x)))
        if not self.index:raise ValueError('Empty role')

    def __len__(self):return len(self.index)

    def __getitem__(self,index):
        case,z,exam=self.index[index];x,y=self.arrays[case]
        return {'image':torch.from_numpy(x[z].astype(np.float32)/255),
                'target':torch.from_numpy(y[z].astype(np.float32)), 'exam_id':exam,'canonical_z':z}
