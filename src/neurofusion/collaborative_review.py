"""Authenticated local review with blind submissions and approved immutable exports."""
from contextlib import contextmanager
import gzip
import hashlib
import hmac
from io import BytesIO
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time
import zipfile
import nibabel as nib
import numpy as np
from neurofusion.cohort_review import CohortReview,ReviewConflict
from neurofusion.external_import import digest


def sha(data):return hashlib.sha256(data).hexdigest()
def password_hash(password,salt):
    if not isinstance(password,str) or not 12<=len(password)<=128:raise ValueError('Password must contain 12–128 characters')
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=32768,r=8,p=1,maxmem=64*1024*1024).hex()


class Collaboration:
    def __init__(self,acquisition,storage,development_partitions=None):
        self.root=Path(storage);self.root.mkdir(parents=True,exist_ok=True)
        self.cohort=CohortReview(acquisition,self.root/'source-workbench')
        self.development_partitions=Path(development_partitions) if development_partitions else None
        self.development_sha256=digest(self.development_partitions) if self.development_partitions else None
        self.db=self.root/'collaboration.sqlite3'
        with self.connection() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, role TEXT NOT NULL, salt TEXT NOT NULL, password TEXT NOT NULL, active INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY, name TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS failures (name TEXT PRIMARY KEY, count INTEGER NOT NULL, until REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS assignments (exam TEXT NOT NULL, reviewer TEXT NOT NULL, PRIMARY KEY(exam,reviewer));
            CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, exam TEXT NOT NULL, reviewer TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(exam,reviewer));
            CREATE TABLE IF NOT EXISTS adjudications (exam TEXT PRIMARY KEY, actor TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS exports (id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, actor TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS selection_batches (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS selection_cases (exam TEXT PRIMARY KEY, batch TEXT NOT NULL, rank INTEGER NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        c=sqlite3.connect(self.db,timeout=15);c.row_factory=sqlite3.Row
        try:
            c.execute('BEGIN IMMEDIATE');yield c;c.commit()
        except Exception:c.rollback();raise
        finally:c.close()

    def log(self,c,actor,action,detail):c.execute('INSERT INTO audit(actor,action,detail,created) VALUES(?,?,?,?)',(actor,action,json.dumps(detail),time.time()))

    def _create(self,c,name,password,role,actor):
        if not isinstance(name,str) or not re.fullmatch('[a-z][a-z0-9_-]{2,39}',name):raise ValueError('Username: 3–40 lowercase letters/digits, hyphen or underscore')
        if role not in ('admin','reviewer','adjudicator'):raise ValueError('Invalid role')
        salt=secrets.token_hex(16);hashed=password_hash(password,salt)
        try:c.execute('INSERT INTO users VALUES(?,?,?,?,1)',(name,role,salt,hashed))
        except sqlite3.IntegrityError:raise ValueError('Account already exists')
        self.log(c,actor,'create_account',{'name':name,'role':role})

    def bootstrap(self,name,password):
        with self.connection() as c:
            if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]:raise ValueError('Bootstrap already completed')
            self._create(c,name,password,'admin','local-bootstrap')

    def login(self,name,password):
        if not isinstance(name,str) or len(name)>40 or not isinstance(password,str) or len(password)>128:raise PermissionError('Invalid credentials')
        success=False;token=None
        with self.connection() as c:
            fail=c.execute('SELECT * FROM failures WHERE name=?',(name,)).fetchone()
            if fail and fail['until']>time.time():raise PermissionError('Login temporarily unavailable')
            row=c.execute('SELECT * FROM users WHERE name=?',(name,)).fetchone()
            try:hashed=password_hash(password,row['salt'] if row else '00'*16)
            except ValueError:hashed=''
            if row and row['active'] and hmac.compare_digest(hashed,row['password']):
                token=secrets.token_urlsafe(32);expires=time.time()+8*3600
                c.execute('INSERT INTO sessions VALUES(?,?,?)',(sha(token.encode()),name,expires))
                c.execute('DELETE FROM failures WHERE name=?',(name,));self.log(c,name,'login',{})
                success=True;role=row['role']
            else:
                count=(fail['count'] if fail and fail['until']==0 else 0)+1
                c.execute('INSERT OR REPLACE INTO failures VALUES(?,?,?)',(name,count,time.time()+300 if count>=5 else 0))
        if not success:raise PermissionError('Invalid credentials')
        return {'token':token,'name':name,'role':role,'expires':expires}

    def actor(self,c,token,roles=None):
        if not isinstance(token,str) or len(token)>128:raise PermissionError('Login required')
        row=c.execute('SELECT u.name,u.role FROM sessions s JOIN users u ON u.name=s.name WHERE s.hash=? AND s.expires>? AND u.active=1',(sha(token.encode()),time.time())).fetchone()
        if row is None or (roles and row['role'] not in roles):raise PermissionError('Not authorized')
        return dict(row)

    def logout(self,token):
        with self.connection() as c:
            actor=self.actor(c,token);c.execute('DELETE FROM sessions WHERE hash=?',(sha(token.encode()),));self.log(c,actor['name'],'logout',{})

    def create_user(self,token,name,password,role):
        with self.connection() as c:
            actor=self.actor(c,token,['admin']);self._create(c,name,password,role,actor['name'])

    def deactivate(self,token,name):
        with self.connection() as c:
            actor=self.actor(c,token,['admin'])
            if name==actor['name']:raise ValueError('Cannot deactivate your own account')
            if c.execute('UPDATE users SET active=0 WHERE name=?',(name,)).rowcount!=1:raise ValueError('Unknown user')
            c.execute('DELETE FROM sessions WHERE name=?',(name,));self.log(c,actor['name'],'deactivate',{'name':name})

    def assign(self,token,exam,reviewers):
        if not isinstance(reviewers,list) or len(reviewers)!=2 or len(set(reviewers))!=2:raise ValueError('Exactly two different reviewers required')
        with self.connection() as c:
            actor=self.actor(c,token,['admin']);self.cohort._verify(exam)
            if c.execute('SELECT 1 FROM assignments WHERE exam=?',(exam,)).fetchone():raise ReviewConflict('Assignments are locked once created')
            for name in reviewers:
                if not c.execute("SELECT 1 FROM users WHERE name=? AND role='reviewer' AND active=1",(name,)).fetchone():raise ValueError('Active reviewer accounts required')
                c.execute('INSERT INTO assignments VALUES(?,?)',(exam,name))
            self.log(c,actor['name'],'assign',{'exam':exam,'reviewers':reviewers})

    def access(self,c,actor,exam):
        if exam not in self.cohort.records:raise ValueError('Unknown case')
        if actor['role']=='reviewer' and not c.execute('SELECT 1 FROM assignments WHERE exam=? AND reviewer=?',(exam,actor['name'])).fetchone():raise PermissionError('Case not assigned')

    def dashboard(self,token):
        with self.connection() as c:
            actor=self.actor(c,token);cases=[]
            for exam in self.cohort.records:
                assigned=[r[0] for r in c.execute('SELECT reviewer FROM assignments WHERE exam=? ORDER BY reviewer',(exam,))]
                if actor['role']=='reviewer' and actor['name'] not in assigned:continue
                reviews=[dict(r) for r in c.execute('SELECT id,reviewer,payload FROM submissions WHERE exam=?',(exam,))]
                decision=c.execute('SELECT payload FROM adjudications WHERE exam=?',(exam,)).fetchone()
                visible=[{'id':r['id'],'reviewer':r['reviewer'],**json.loads(r['payload'])} for r in reviews if r['reviewer']==actor['name'] or (actor['role']=='adjudicator' and len(reviews)==2)]
                disagreement=None
                if actor['role']=='adjudicator' and len(reviews)==2:
                    a,b=[json.loads(r['payload']) for r in reviews]
                    disagreement=(a['decision'],a.get('mask_sha256'))!=(b['decision'],b.get('mask_sha256'))
                cases.append({'exam':exam,'assigned':assigned,'submission_count':len(reviews),'submissions':visible,'disagreement':disagreement,
                              'adjudication':json.loads(decision[0]) if decision else None})
            users=[dict(r) for r in c.execute('SELECT name,role,active FROM users ORDER BY name')] if actor['role']=='admin' else []
            return {'actor':actor,'cases':cases,'users':users,'credentials_verified':False,'qualification_promoted':False}

    def import_selection(self,token,candidates,protected_patients,budget,reviewers,seed=42):
        """Select and assign atomically against a server-configured development allowlist."""
        from neurofusion.active_learning import select_annotations
        with self.connection() as c:
            actor=self.actor(c,token,['admin'])
            if self.development_partitions is None:raise ValueError('Development partition allowlist is not configured; protected review cohort cannot be selected')
            if digest(self.development_partitions)!=self.development_sha256:raise ValueError('Development partitions changed')
            parts=json.loads(self.development_partitions.read_text(encoding='utf-8'))['records']
            allowed={r['exam_id']:r for r in parts if r['role']=='train'}
            protected=set(protected_patients)|{r['patient_id'] for r in parts if r['role']!='train'}
            if not isinstance(reviewers,list) or len(reviewers)!=2 or len(set(reviewers))!=2:raise ValueError('Two different reviewers required')
            for name in reviewers:
                if not c.execute("SELECT 1 FROM users WHERE name=? AND role='reviewer' AND active=1",(name,)).fetchone():raise ValueError('Active reviewer accounts required')
            for row in candidates:
                source=allowed.get(row['case_id'])
                if source is None or row['patient_id']!=source['patient_id'] or row['input_sha256']!=source['image']['sha256']:raise ValueError('Candidate is not bound to an allowed training source')
                self.cohort._verify(row['case_id'])
                if self.cohort.records[row['case_id']]['files'][0]['sha256']!=row['input_sha256']:raise ValueError('Review source differs')
                if c.execute('SELECT 1 FROM assignments WHERE exam=?',(row['case_id'],)).fetchone():raise ReviewConflict('Candidate already assigned')
            result=select_annotations(candidates,protected_patients=protected,budget=budget,seed=seed)
            identity=secrets.token_hex(16)
            result.update(batch_id=identity,created=time.time(),created_by=actor['name'],partition_sha256=self.development_sha256,reviewers=reviewers)
            for row in result['selected']:
                for name in reviewers:c.execute('INSERT INTO assignments VALUES(?,?)',(row['case_id'],name))
                c.execute('INSERT INTO selection_cases VALUES(?,?,?)',(row['case_id'],identity,row['rank']))
            c.execute('INSERT INTO selection_batches VALUES(?,?)',(identity,json.dumps(result)))
            self.log(c,actor['name'],'active_learning_assign',{'batch_id':identity,'budget':budget})
            return result

    def selection_status(self,token):
        with self.connection() as c:
            self.actor(c,token,['admin','adjudicator']);batches=[]
            for batch in c.execute('SELECT payload FROM selection_batches'):
                row=json.loads(batch[0]);progress=[]
                for selected in row['selected']:
                    exam=selected['case_id'];decision=c.execute('SELECT payload FROM adjudications WHERE exam=?',(exam,)).fetchone()
                    reviews=[json.loads(r[0]) for r in c.execute('SELECT payload FROM submissions WHERE exam=?',(exam,))]
                    progress.append({'exam':exam,'submitted':len(reviews),'adjudication':json.loads(decision[0]) if decision else None,'reported_annotation_minutes':sum(r.get('annotation_minutes') or 0 for r in reviews),'effort_reports':sum(r.get('annotation_minutes') is not None for r in reviews)})
                batches.append({'selection':row,'progress':progress})
            return batches

    def source_details(self,token,exam):
        with self.connection() as c:self.access(c,self.actor(c,token),exam)
        details=self.cohort.details(exam)
        return {k:v for k,v in details.items() if k not in ('reviews','revision')}

    def source_slice(self,token,exam,axis,index,overlay):
        with self.connection() as c:self.access(c,self.actor(c,token),exam)
        return self.cohort.slice_png(exam,axis,index,overlay)

    def validated_mask(self,exam,data):
        if not isinstance(data,bytes) or not 0<len(data)<=25*1024*1024:raise ValueError('Mask upload limit is 25 MiB')
        paths=self.cohort._verify(exam);image=nib.load(paths[0])
        if data[:2]==b'\x1f\x8b':
            with gzip.GzipFile(fileobj=BytesIO(data)) as stream:raw=stream.read(80*1024*1024+1)
        else:raw=data
        if len(raw)>80*1024*1024:raise ValueError('Expanded mask limit exceeded')
        mask=nib.Nifti1Image.from_bytes(raw)
        if mask.shape!=image.shape or not np.allclose(mask.affine,image.affine,atol=1e-4,rtol=0) or mask.header.get_xyzt_units()[0]!=image.header.get_xyzt_units()[0]:raise ValueError('Mask must match original image geometry and units')
        for volume in (image,mask):
            q,qc=volume.get_qform(coded=True);s,sc=volume.get_sform(coded=True)
            if qc and sc and not np.allclose(q,s,atol=1e-4,rtol=0):raise ValueError('Conflicting qform/sform')
        values=mask.get_fdata(dtype=np.float32)
        if not np.isfinite(values).all() or not np.isin(values,[0,1,2,4]).all():raise ValueError('Numeric labels must be 0, 1, 2, 4')
        canonical=nib.Nifti1Image(values.astype(np.uint8),image.affine);canonical.header.set_xyzt_units(*image.header.get_xyzt_units())
        return canonical.to_bytes()

    def submit(self,token,exam,payload,mask_data=None):
        with self.connection() as c:
            actor=self.actor(c,token,['reviewer']);self.access(c,actor,exam)
            if c.execute('SELECT 1 FROM submissions WHERE exam=? AND reviewer=?',(exam,actor['name'])).fetchone():raise ReviewConflict('Submitted annotations are immutable')
            self.cohort._verify(exam);row=self.cohort.records[exam]
            if payload.get('manifest_sha256')!=self.cohort.manifest_sha256 or payload.get('image_sha256')!=row['files'][0]['sha256']:raise ReviewConflict('Source binding differs')
            decision=payload.get('decision');notes=payload.get('notes')
            if decision not in ('accept','exclude','needs_followup') or not isinstance(notes,str) or not 1<=len(notes.strip())<=6000:raise ValueError('Decision and rationale required')
            if payload.get('whole_volume_reviewed') is not True:raise ValueError('Whole-volume review acknowledgement required')
            if decision=='accept' and mask_data is None:raise ValueError('Accepted annotation requires an independent mask upload')
            if decision!='accept' and mask_data is not None:raise ValueError('Only accept submissions contain masks')
            record={'decision':decision,'notes':notes,'whole_volume_reviewed':True,'manifest_sha256':self.cohort.manifest_sha256,
                    'image_sha256':row['files'][0]['sha256'],'source_mask_sha256':row['files'][1]['sha256'],'created':time.time(),'mask_sha256':None}
            minutes=payload.get('annotation_minutes')
            if minutes is not None and (type(minutes) not in (int,float) or not np.isfinite(minutes) or not 0<minutes<=10080):raise ValueError('Annotation effort must be finite positive minutes')
            if c.execute('SELECT 1 FROM selection_cases WHERE exam=?',(exam,)).fetchone() and minutes is None:raise ValueError('Active-learning reviews require reported annotation minutes')
            record['annotation_minutes']=minutes
            if mask_data is not None:
                data=self.validated_mask(exam,mask_data);checksum=sha(data);folder=self.root/'annotations';folder.mkdir(exist_ok=True)
                path=folder/(checksum+'.nii')
                if path.exists():
                    if digest(path)!=checksum:raise ValueError('Stored annotation corrupted')
                else:
                    with path.open('xb') as handle:handle.write(data)
                record['mask_sha256']=checksum
            cur=c.execute('INSERT INTO submissions(exam,reviewer,payload) VALUES(?,?,?)',(exam,actor['name'],json.dumps(record)))
            self.log(c,actor['name'],'submit',{'exam':exam,'submission_id':cur.lastrowid})
            return {'id':cur.lastrowid,**record}

    def adjudicate(self,token,exam,submission_ids,decision,chosen_id,notes):
        with self.connection() as c:
            actor=self.actor(c,token,['adjudicator']);self.access(c,actor,exam);self.cohort._verify(exam)
            if c.execute('SELECT 1 FROM adjudications WHERE exam=?',(exam,)).fetchone():raise ReviewConflict('Adjudication is immutable')
            reviews=list(c.execute('SELECT * FROM submissions WHERE exam=? ORDER BY id',(exam,)))
            if len(reviews)!=2 or sorted(submission_ids)!=[r['id'] for r in reviews]:raise ReviewConflict('Two exact submitted review IDs required')
            if any(r['reviewer']==actor['name'] for r in reviews):raise PermissionError('Cannot adjudicate own annotation')
            if decision not in ('approve','exclude') or not isinstance(notes,str) or not 1<=len(notes.strip())<=6000:raise ValueError('Adjudication decision and rationale required')
            selected=next((r for r in reviews if r['id']==chosen_id),None)
            mask_sha=None
            if decision=='approve':
                if selected is None:raise ValueError('Choose a submitted annotation')
                chosen=json.loads(selected['payload']);mask_sha=chosen['mask_sha256']
                if chosen['decision']!='accept' or mask_sha is None:raise ValueError('Chosen submission must contain an accepted mask')
                if digest(self.root/'annotations'/(mask_sha+'.nii'))!=mask_sha:raise ValueError('Annotation checksum changed')
            elif chosen_id is not None:raise ValueError('Excluded cases have no chosen annotation')
            record={'decision':decision,'submission_ids':[r['id'] for r in reviews],'chosen_id':chosen_id,'mask_sha256':mask_sha,
                    'adjudicator':actor['name'],'notes':notes,'created':time.time(),'credentials_verified':False,'qualification_promoted':False}
            c.execute('INSERT INTO adjudications VALUES(?,?,?)',(exam,actor['name'],json.dumps(record)))
            self.log(c,actor['name'],'adjudicate',{'exam':exam,**record});return record

    def export(self,token,exams):
        if not isinstance(exams,list) or not exams or len(exams)!=len(set(exams)):raise ValueError('Select unique approved cases')
        with self.connection() as c:
            actor=self.actor(c,token,['admin','adjudicator']);records=[];masks={}
            for exam in sorted(exams):
                self.cohort._verify(exam)
                row=c.execute('SELECT payload FROM adjudications WHERE exam=?',(exam,)).fetchone()
                if row is None:raise ReviewConflict('Every exported case must be adjudicated')
                approval=json.loads(row[0])
                if approval['decision']!='approve':raise ReviewConflict('Excluded cases cannot export labels')
                checksum=approval['mask_sha256'];path=self.root/'annotations'/(checksum+'.nii');data=path.read_bytes()
                if sha(data)!=checksum:raise ValueError('Approved label changed')
                sources=self.cohort.records[exam]
                reviews=[{'id':r['id'],'reviewer':r['reviewer'],**json.loads(r['payload'])} for r in c.execute('SELECT * FROM submissions WHERE exam=? ORDER BY id',(exam,))]
                records.append({'exam':exam,'patient_id':sources['patient_id'],'source_files':[{k:f[k] for k in ('path','sha256') } for f in sources['files']],'adjudication':approval,'reviews':reviews,'label_path':f'labels/{exam}.nii','label_sha256':checksum})
                selection=c.execute('SELECT batch,rank FROM selection_cases WHERE exam=?',(exam,)).fetchone()
                records[-1]['active_learning']=dict(selection) if selection else None
                if selection:
                    batch=json.loads(c.execute('SELECT payload FROM selection_batches WHERE id=?',(selection['batch'],)).fetchone()[0])
                    records[-1]['active_learning']['selection_provenance']=batch
                masks[f'labels/{exam}.nii']=data
            export_id=secrets.token_hex(16);manifest={'schema_version':1,'export_id':export_id,'created':time.time(),'exported_by':actor['name'],
                'source_manifest_sha256':self.cohort.manifest_sha256,'records':records,'research_only':True,'reviewer_credentials_verified':False,
                'clinical_ready':False,'qualification_promoted':False,'training_eligibility':'Not authorized by export; original cohort restrictions remain in force'}
            output=BytesIO()
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('manifest.json',json.dumps(manifest,indent=2))
                for name,data in masks.items():archive.writestr(name,data)
            data=output.getvalue();folder=self.root/'exports';folder.mkdir(exist_ok=True)
            with (folder/(export_id+'.zip')).open('xb') as handle:handle.write(data)
            c.execute('INSERT INTO exports VALUES(?,?,?,?)',(export_id,sha(data),actor['name'],time.time()))
            self.log(c,actor['name'],'export',{'id':export_id,'sha256':sha(data),'exams':exams})
            return {'export_id':export_id,'sha256':sha(data),'cases':len(records)}

    def download_export(self,token,identity):
        if not re.fullmatch('[0-9a-f]{32}',identity):raise ValueError('Invalid export ID')
        with self.connection() as c:
            self.actor(c,token,['admin','adjudicator']);row=c.execute('SELECT sha256 FROM exports WHERE id=?',(identity,)).fetchone()
            if row is None:raise ValueError('Unknown export')
            data=(self.root/'exports'/(identity+'.zip')).read_bytes()
            if sha(data)!=row[0]:raise ValueError('Export checksum changed')
            return data

    def annotation(self,token,submission_id):
        with self.connection() as c:
            actor=self.actor(c,token)
            row=c.execute('SELECT * FROM submissions WHERE id=?',(submission_id,)).fetchone()
            if row is None:raise ValueError('Unknown annotation')
            count=c.execute('SELECT COUNT(*) FROM submissions WHERE exam=?',(row['exam'],)).fetchone()[0]
            if not (actor['name']==row['reviewer'] or (actor['role']=='adjudicator' and count==2)):raise PermissionError('Annotation is blinded')
            self.cohort._verify(row['exam'])
            checksum=json.loads(row['payload'])['mask_sha256']
            if checksum is None:raise ValueError('Submission has no mask')
            data=(self.root/'annotations'/(checksum+'.nii')).read_bytes()
            if sha(data)!=checksum:raise ValueError('Annotation checksum changed')
            return row['exam'],data

    def annotation_slice(self,token,submission_id,axis,index):
        from PIL import Image
        exam,data=self.annotation(token,submission_id)
        gray,_,_,_=self.cohort._load(exam)
        if axis not in range(3) or not 0<=index<gray.shape[axis]:raise ValueError('Invalid slice')
        mask=nib.as_closest_canonical(nib.Nifti1Image.from_bytes(data)).get_fdata()
        plane=np.rot90(np.take(gray,index,axis=axis));labels=np.rot90(np.take(mask,index,axis=axis))
        rgb=np.repeat(plane[:,:,None],3,axis=2)
        for value,color in [(1,(255,90,90)),(2,(90,230,140)),(4,(80,155,255))]:
            selected=labels==value;rgb[selected]=np.rint(rgb[selected]*.5+np.array(color)*.5).astype(np.uint8)
        output=BytesIO();Image.fromarray(rgb).save(output,format='PNG');return output.getvalue()

    def source_download(self,token,exam):
        with self.connection() as c:self.access(c,self.actor(c,token),exam)
        return self.cohort._verify(exam)[0].read_bytes()

    def audit(self,token):
        with self.connection() as c:
            self.actor(c,token,['admin'])
            return [dict(row) for row in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 500')]

    def reset_password(self,token,name,password):
        with self.connection() as c:
            actor=self.actor(c,token,['admin']);salt=secrets.token_hex(16)
            hashed=password_hash(password,salt)
            if c.execute('UPDATE users SET salt=?,password=? WHERE name=?',(salt,hashed,name)).rowcount!=1:raise ValueError('Unknown account')
            c.execute('DELETE FROM sessions WHERE name=?',(name,))
            c.execute('DELETE FROM failures WHERE name=?',(name,))
            self.log(c,actor['name'],'reset_password',{'name':name})
