"""Disk-backed single-study access for frozen train/validation partitions."""
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from neurofusion.data import audit, save_json
from neurofusion.preprocessing import prepare_dwi


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            value.update(block)
    return value.hexdigest()


class StudyStore:
    """No cohort-wide voxel cache. Each load returns only the requested study."""
    version='dwi-native-ras-zscore-v1'

    def __init__(self,manifest_path,splits_path,cache):
        self.manifest_path=Path(manifest_path)
        self.splits_path=Path(splits_path)
        self.manifest=json.loads(self.manifest_path.read_text())
        self.splits=json.loads(self.splits_path.read_text())
        if not self.splits.get('frozen') or self.splits.get('manifest_sha256')!=digest(self.manifest_path):
            raise ValueError('Frozen splits must match the manifest hash')
        if not audit(self.manifest,self.splits)['passed']:
            raise ValueError('Manifest/split audit failed')
        self.root=Path(self.manifest['data_root']).resolve()
        self.cache=Path(cache).resolve()/self.version/digest(self.manifest_path)[:16]
        self.verified=set()
        self.max_study_bytes=0

    def studies(self,partition):
        if partition not in ('train','validation'):
            raise ValueError('This development loader cannot access holdout data')
        return sorted([s for s in self.manifest['studies'] if self.splits['assignments'][s['subject_id']]==partition],
                      key=lambda s:(s['subject_id'],s['study_id']))

    def _paths(self,study):
        identity=(study['subject_id'],study['study_id'])
        if not any((s['subject_id'],s['study_id'])==identity for p in ('train','validation') for s in self.studies(p)):
            raise ValueError('Study not in allowed partitions')
        # Use authoritative manifest entries, not caller-supplied file paths.
        authoritative=next(s for s in self.manifest['studies'] if (s['subject_id'],s['study_id'])==identity)
        paths=[(self.root/authoritative['files'][k]['path']).resolve() for k in ('dwi','mask')]
        if not all(p.is_relative_to(self.root) for p in paths):
            raise ValueError('Source escapes data root')
        key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
        return authoritative,paths,self.cache/key

    def prepare(self,study):
        study,paths,folder=self._paths(study)
        identity=(study['subject_id'],study['study_id'])
        if identity not in self.verified:
            if any(digest(p)!=study['files'][k]['sha256'] for k,p in zip(('dwi','mask'),paths)):
                raise ValueError('Raw source changed since manifest creation')
        marker=folder/'cache.json'
        if marker.exists():
            record=json.loads(marker.read_text())
            if record['version']!=self.version or record['source']!={k:study['files'][k]['sha256'] for k in ('dwi','mask')}:
                raise ValueError('Incompatible cache provenance')
            if identity not in self.verified:
                for name,checksum in record['artifacts'].items():
                    if Path(name).name!=name or digest(folder/name)!=checksum:
                        raise ValueError('Corrupted preprocessing cache')
        else:
            folder.mkdir(parents=True,exist_ok=True)
            # Interrupted cache construction is explicit, never silently reused.
            prepared=folder/'prepared'
            meta=prepare_dwi(paths[0],paths[1],prepared)
            x=nib.load(prepared/'dwi.nii.gz').get_fdata(dtype=np.float32)
            y=nib.load(prepared/'mask.nii.gz').get_fdata(dtype=np.float32).astype(np.uint8)
            np.save(folder/'image.npy',x,allow_pickle=False)
            np.save(folder/'mask.npy',y,allow_pickle=False)
            save_json(folder/'transform.json',meta)
            record={'version':self.version,'source':{k:study['files'][k]['sha256'] for k in ('dwi','mask')},
                    'artifacts':{n:digest(folder/n) for n in ('image.npy','mask.npy','transform.json')}}
            save_json(marker,record)
        self.verified.add(identity)
        return folder

    def load(self,study):
        folder=self.prepare(study)
        x=np.load(folder/'image.npy',mmap_mode='r',allow_pickle=False)
        y=np.load(folder/'mask.npy',mmap_mode='r',allow_pickle=False)
        if x.ndim!=3 or x.shape!=y.shape:
            raise ValueError('Invalid cached array shape')
        self.max_study_bytes=max(self.max_study_bytes,x.nbytes+y.nbytes)
        return x,y,json.loads((folder/'transform.json').read_text())


def epoch_order(count,seed,epoch):
    if count<1 or epoch<1:
        raise ValueError('Positive study count and epoch required')
    return np.random.default_rng(seed+epoch).permutation(count).tolist()
