"""Local, source-pinned full-volume review. No model execution or gate promotion."""
from collections import OrderedDict
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import threading

import nibabel as nib
import numpy as np
from PIL import Image

from neurofusion.external_import import digest
from neurofusion.exposure import validate_review
from neurofusion.pdgm import audit_volume_pair, identity

PLANES = [('Sagittal', 'left P / right A; top S'),
          ('Coronal', 'left L / right R; top S'),
          ('Axial', 'left L / right R; top A')]


class ReviewConflict(ValueError):
    pass


class CohortReview:
    def __init__(self, acquisition, storage):
        self.acquisition = Path(acquisition).resolve()
        self.storage = Path(storage)
        manifest = self.acquisition/'summary.json'
        self.manifest_sha256 = digest(manifest)
        records = json.loads(manifest.read_text(encoding='utf-8'))['results']
        self.records = {}
        for row in records:
            patient, exam, _ = identity(row['exam_id'])
            if row['status'] != 'integrity_verified' or patient != row['patient_id'] or exam in self.records:
                raise ValueError('Unverified or duplicate review case')
            expected = [exam+'_T1c.nii.gz', exam+'_tumor_segmentation.nii.gz']
            if len(row['files']) != 2:
                raise ValueError('Exactly two source files required')
            for f, name in zip(row['files'], expected):
                p=(self.acquisition/f['path']).resolve()
                if not p.is_relative_to(self.acquisition) or p.name != name:
                    raise ValueError('Invalid review source path')
            self.records[exam] = row
        self.storage.mkdir(parents=True, exist_ok=True)
        self.db = self.storage/'reviews.sqlite3'
        self.lock = threading.RLock()
        self.cache = OrderedDict()
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS cohort_reviews (exam TEXT, revision INTEGER, payload TEXT NOT NULL, PRIMARY KEY(exam,revision))')

    def _sources(self, exam):
        if exam not in self.records:
            raise ValueError('Unknown review case')
        return [(self.acquisition/f['path']).resolve() for f in self.records[exam]['files']]

    def _verify(self, exam):
        if digest(self.acquisition/'summary.json') != self.manifest_sha256:
            raise ValueError('Acquisition inventory changed; reopen the workbench')
        paths=self._sources(exam)
        if any(not p.is_relative_to(self.acquisition) for p in paths):
            raise ValueError('Source escaped acquisition directory')
        for p, f in zip(paths, self.records[exam]['files']):
            if digest(p) != f['sha256']:
                raise ValueError('Source checksum changed')
        return paths

    def _load(self, exam):
        with self.lock:
            paths=self._verify(exam)
            if exam in self.cache:
                self.cache.move_to_end(exam)
                return self.cache[exam]
            audit_volume_pair(*paths, allowed_labels=[0,1,2,4])
            volumes=[nib.as_closest_canonical(nib.load(p)) for p in paths]
            affine=volumes[0].affine
            if not np.allclose(affine[:3,:3],np.diag(np.diag(affine[:3,:3])),atol=1e-4):
                raise ValueError('Oblique grids require a separate display policy')
            for volume in volumes:
                q,qcode=volume.get_qform(coded=True);s,scode=volume.get_sform(coded=True)
                if qcode and scode and not np.allclose(q,s,atol=1e-4):
                    raise ValueError('Conflicting qform and sform')
            data=volumes[0].get_fdata(dtype=np.float32)
            labels=volumes[1].get_fdata(dtype=np.float32).astype(np.uint8)
            low,high=np.percentile(data[data!=0],[1,99])
            if high<=low: raise ValueError('Invalid display window')
            gray=np.rint(np.where(data!=0,np.clip((data-low)/(high-low),0,1),0)*255).astype(np.uint8)
            value=(gray,labels,affine.copy(),[float(low),float(high)])
            self._verify(exam)
            self.cache[exam]=value
            while len(self.cache)>2:self.cache.popitem(last=False)
            return value

    def history(self, exam):
        self._sources(exam)
        with sqlite3.connect(self.db) as conn:
            rows=conn.execute('SELECT payload FROM cohort_reviews WHERE exam=? ORDER BY revision',(exam,)).fetchall()
        return {'exam_id':exam,'revision':len(rows),'reviews':[json.loads(r[0]) for r in rows],
                'reviewer_identity_verified':False,'qualification_promoted':False}

    def cases(self):
        result=[]
        for exam,row in self.records.items():
            history=self.history(exam)
            result.append({'exam_id':exam,'patient_id':row['patient_id'],'revision':history['revision'],
                           'latest_decision':history['reviews'][-1]['decision'] if history['reviews'] else 'pending'})
        return {'cases':result,'reviewer_identity_verified':False,'qualification_promoted':False}

    def details(self, exam):
        gray,_,affine,window=self._load(exam)
        return {'exam_id':exam,'shape':list(gray.shape),'spacing_mm':nib.affines.voxel_sizes(affine).tolist(),
                'canonical_affine':affine.tolist(),'orientation':'RAS','window_p1_p99':window,
                'planes':[{'name':n,'directions':d} for n,d in PLANES],
                'image_sha256':self.records[exam]['files'][0]['sha256'],
                'mask_sha256':self.records[exam]['files'][1]['sha256'],
                'manifest_sha256':self.manifest_sha256,**self.history(exam)}

    def slice_png(self, exam, axis, index, overlay):
        if type(axis) is not int or axis not in range(3) or type(index) is not int or type(overlay) is not bool:
            raise ValueError('Invalid slice request')
        gray,labels,_,_=self._load(exam)
        if not 0<=index<gray.shape[axis]:raise ValueError('Slice outside volume')
        plane=np.rot90(np.take(gray,index,axis=axis))
        rgb=np.repeat(plane[:,:,None],3,axis=2)
        if overlay:
            lab=np.rot90(np.take(labels,index,axis=axis))
            for value,color in [(1,(255,90,90)),(2,(90,230,140)),(4,(80,155,255))]:
                selected=lab==value
                rgb[selected]=np.rint(rgb[selected]*.5+np.array(color)*.5).astype(np.uint8)
        output=BytesIO();Image.fromarray(rgb).save(output,format='PNG')
        return output.getvalue()

    def submit(self, exam, payload):
        if not isinstance(payload,dict):raise ValueError('Review object required')
        self._verify(exam)
        if type(payload.get('expected_revision')) is not int or payload['expected_revision']<0:
            raise ValueError('Expected revision required')
        if payload.get('manifest_sha256')!=self.manifest_sha256:
            raise ReviewConflict('Inventory version differs')
        for k,f in zip(('image_sha256','mask_sha256'),self.records[exam]['files']):
            if payload.get(k)!=f['sha256']:raise ReviewConflict('Review source hashes differ')
        for key,limit in [('reviewer_name',120),('reviewer_qualification',300),('notes',6000),('reviewed_at',60)]:
            if not isinstance(payload.get(key),str) or not 0<len(payload[key].strip())<=limit:
                raise ValueError('Invalid '+key)
        if payload.get('decision')=='pending':raise ValueError('Choose a submitted decision')
        validate_review(payload)
        with self.lock,sqlite3.connect(self.db,timeout=10) as conn:
            conn.execute('BEGIN IMMEDIATE')
            revision=conn.execute('SELECT COUNT(*) FROM cohort_reviews WHERE exam=?',(exam,)).fetchone()[0]
            if revision!=payload['expected_revision']:raise ReviewConflict('A newer review exists; reload history before submitting')
            keys=('reviewer_name','reviewer_qualification','reviewed_at','notes','decision',
                  'whole_volume_reviewed','identity_checked','orientation_checked','alignment_checked',
                  'image_sha256','mask_sha256','manifest_sha256')
            entry={k:payload.get(k) for k in keys}
            entry.update(exam_id=exam,patient_id=self.records[exam]['patient_id'],revision=revision+1,
                         received_at=datetime.now(timezone.utc).isoformat(),reviewer_identity_verified=False,
                         qualification_promoted=False)
            conn.execute('INSERT INTO cohort_reviews VALUES (?,?,?)',(exam,revision+1,json.dumps(entry,allow_nan=False)))
        return entry
