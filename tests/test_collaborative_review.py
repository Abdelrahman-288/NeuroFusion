import importlib.util
import json
from io import BytesIO
from pathlib import Path
import threading
import urllib.request
import urllib.error
import zipfile
import nibabel as nib
import numpy as np
import pytest
from neurofusion.collaborative_review import Collaboration, sha, ReviewConflict

PASSWORD = 'Synthetic-test-only-123!'
EXAM = 'UCSF-PDGM-0001'


@pytest.fixture
def setup(tmp_path):
    acq = tmp_path/'acquisition'; acq.mkdir(); files=[]
    for index, suffix in enumerate(('T1c', 'tumor_segmentation')):
        data = np.arange(120, dtype=np.float32).reshape(4,5,6) if index == 0 else np.zeros((4,5,6), dtype=np.uint8)
        volume = nib.Nifti1Image(data, np.diag([1.,2.,3.,1.])); volume.header.set_xyzt_units('mm')
        path=acq/f'{EXAM}_{suffix}.nii.gz'; nib.save(volume,path)
        files.append({'path':path.name,'sha256':sha(path.read_bytes())})
    (acq/'summary.json').write_text(json.dumps({'results':[{'exam_id':EXAM,'patient_id':EXAM,'status':'integrity_verified','files':files}]}))
    store=Collaboration(acq,tmp_path/'store');store.bootstrap('admin',PASSWORD)
    admin=store.login('admin',PASSWORD)['token'];tokens={'admin':admin}
    for name,role in [('one','reviewer'),('two','reviewer'),('outsider','reviewer'),('judge','adjudicator')]:
        store.create_user(admin,name,PASSWORD,role);tokens[name]=store.login(name,PASSWORD)['token']
    store.assign(admin,EXAM,['one','two'])
    mask=nib.Nifti1Image(np.zeros((4,5,6),dtype=np.uint8),np.diag([1.,2.,3.,1.]));mask.header.set_xyzt_units('mm')
    payload={'decision':'accept','notes':'Synthetic review','whole_volume_reviewed':True,'manifest_sha256':store.cohort.manifest_sha256,'image_sha256':files[0]['sha256']}
    return store,tokens,mask,payload


def test_independent_review_adjudication_export(setup):
    s,t,mask,p=setup
    with pytest.raises(PermissionError):s.source_details(t['outsider'],EXAM)
    with pytest.raises(ReviewConflict):s.export(t['admin'],[EXAM])
    first=s.submit(t['one'],EXAM,p,mask.to_bytes())
    assert not s.dashboard(t['two'])['cases'][0]['submissions']
    assert not s.dashboard(t['judge'])['cases'][0]['submissions']
    with pytest.raises(PermissionError):s.annotation(t['two'],first['id'])
    with pytest.raises(PermissionError):s.annotation(t['judge'],first['id'])
    with pytest.raises(ReviewConflict):s.submit(t['one'],EXAM,p,mask.to_bytes())
    with pytest.raises(ReviewConflict):s.adjudicate(t['judge'],EXAM,[first['id']],'approve',first['id'],'too early')
    values=np.zeros((4,5,6),dtype=np.uint8);values[1,2,3]=4
    secondmask=nib.Nifti1Image(values,mask.affine);secondmask.header.set_xyzt_units('mm')
    second=s.submit(t['two'],EXAM,p,secondmask.to_bytes())
    assert s.dashboard(t['judge'])['cases'][0]['disagreement'] is True
    assert len(s.dashboard(t['one'])['cases'][0]['submissions'])==1
    assert s.annotation_slice(t['judge'],second['id'],2,3).startswith(b'\x89PNG')
    with pytest.raises(PermissionError):s.adjudicate(t['admin'],EXAM,[first['id'],second['id']],'approve',second['id'],'invalid role')
    with pytest.raises(ReviewConflict):s.adjudicate(t['judge'],EXAM,[first['id'],999],'approve',second['id'],'stale')
    s.adjudicate(t['judge'],EXAM,[first['id'],second['id']],'approve',second['id'],'Resolved difference after comparison')
    with pytest.raises(ReviewConflict):s.adjudicate(t['judge'],EXAM,[first['id'],second['id']],'exclude',None,'overwrite')
    result=s.export(t['admin'],[EXAM]);data=s.download_export(t['admin'],result['export_id'])
    assert sha(data)==result['sha256']
    with zipfile.ZipFile(BytesIO(data)) as z:
        m=json.loads(z.read('manifest.json'));row=m['records'][0]
        assert sha(z.read(row['label_path']))==second['mask_sha256']
        assert m['qualification_promoted'] is False and m['reviewer_credentials_verified'] is False
        assert len(row['reviews'])==2
    with pytest.raises(PermissionError):s.download_export(t['one'],result['export_id'])
    (s.root/'annotations'/(second['mask_sha256']+'.nii')).write_bytes(b'tampered')
    with pytest.raises(ValueError):s.export(t['admin'],[EXAM])


def test_account_boundaries(setup):
    s,t,mask,p=setup
    with pytest.raises(ValueError):s.bootstrap('again',PASSWORD)
    with pytest.raises(PermissionError):s.create_user(t['one'],'evil',PASSWORD,'admin')
    with pytest.raises(ValueError):s.deactivate(t['admin'],'admin')
    for _ in range(5):
        with pytest.raises(PermissionError):s.login('outsider','wrong-password')
    with pytest.raises(PermissionError,match='temporarily'):s.login('outsider',PASSWORD)
    s.reset_password(t['admin'],'outsider',PASSWORD+'new')
    with pytest.raises(PermissionError):s.dashboard(t['outsider'])
    s.login('outsider',PASSWORD+'new')
    s.deactivate(t['admin'],'one')
    with pytest.raises(PermissionError):s.submit(t['one'],EXAM,p,mask.to_bytes())
    s.logout(t['two'])
    with pytest.raises(PermissionError):s.dashboard(t['two'])
    with s.connection() as c:
        assert PASSWORD not in c.execute('SELECT password FROM users').fetchone()[0]
        c.execute('UPDATE sessions SET expires=0')
    with pytest.raises(PermissionError):s.dashboard(t['admin'])


def test_mask_and_source_validation(setup):
    s,t,mask,p=setup
    with pytest.raises(ValueError):s.submit(t['one'],EXAM,p)
    with pytest.raises(ReviewConflict):s.submit(t['one'],EXAM,{**p,'image_sha256':'stale'},mask.to_bytes())
    with pytest.raises(ValueError):s.submit(t['one'],EXAM,{**p,'whole_volume_reviewed':False},mask.to_bytes())
    bad=nib.Nifti1Image(np.full((4,5,6),3,dtype=np.uint8),mask.affine);bad.header.set_xyzt_units('mm')
    with pytest.raises(ValueError,match='labels'):s.submit(t['one'],EXAM,p,bad.to_bytes())
    bad=nib.Nifti1Image(np.zeros((4,5,6)),np.eye(4));bad.header.set_xyzt_units('mm')
    with pytest.raises(ValueError,match='geometry'):s.submit(t['one'],EXAM,p,bad.to_bytes())
    with pytest.raises(ReviewConflict):s.assign(t['admin'],EXAM,['one','two'])
    with pytest.raises(ValueError):s.assign(t['admin'],EXAM,['one','one'])
    (s.cohort.acquisition/'summary.json').write_text('{}')
    with pytest.raises(ValueError,match='inventory changed'):s.submit(t['one'],EXAM,p,mask.to_bytes())


def test_exclusion_cannot_export(setup):
    s,t,mask,p=setup
    a=s.submit(t['one'],EXAM,{**p,'decision':'exclude'})
    b=s.submit(t['two'],EXAM,{**p,'decision':'needs_followup'})
    with pytest.raises(ValueError):s.adjudicate(t['judge'],EXAM,[a['id'],b['id']],'approve',a['id'],'invalid')
    s.adjudicate(t['judge'],EXAM,[a['id'],b['id']],'exclude',None,'Unresolved, excluded')
    with pytest.raises(ReviewConflict):s.export(t['admin'],[EXAM])


def test_http_boundary(setup):
    s,t,_,_=setup
    spec=importlib.util.spec_from_file_location('collab_server',Path(__file__).parents[1]/'scripts/serve_collaboration.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    server=mod.ThreadingHTTPServer(('127.0.0.1',0),mod.Handler);server.store=s
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        assert b'Collaborative review' in urllib.request.urlopen(base).read()
        for path,headers in [('/api/dashboard',{}),('/api/dashboard',{'Host':'evil.example'}),('/api/dashboard',{'Authorization':'Bearer '+t['admin'],'Origin':'https://evil.example'})]:
            with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(base+path,headers=headers))
            assert e.value.code==403
        req=urllib.request.Request(base+'/api/dashboard',headers={'Authorization':'Bearer '+t['admin']})
        response=urllib.request.urlopen(req);assert json.load(response)['actor']['role']=='admin'
        assert response.headers['Cache-Control']=='no-store'
        req=urllib.request.Request(base+'/api/login',data=json.dumps({'name':'admin','password':PASSWORD}).encode(),headers={'Content-Type':'application/json'})
        assert 'token' in json.load(urllib.request.urlopen(req))
    finally:server.shutdown();server.server_close();thread.join()


def test_active_learning_assignment_and_approved_provenance(setup,tmp_path):
    s,t,mask,p=setup
    from neurofusion.external_import import digest
    candidate={'case_id':EXAM,'patient_id':EXAM,'partition':'train','role':'unlabeled_development','patient_identity_verified':True,'uncertainty':.8,'embedding':[1.,2.],'embedding_version':'test','uncertainty_method':'entropy','model_sha256':'a'*64,'input_sha256':p['image_sha256']}
    with pytest.raises(ValueError,match='allowlist'):s.import_selection(t['admin'],[candidate],[],1,['one','two'])
    path=tmp_path/'partitions.json';path.write_text(json.dumps({'records':[{'exam_id':EXAM,'patient_id':EXAM,'role':'train','image':{'sha256':p['image_sha256']}}]}))
    s.development_partitions=path;s.development_sha256=digest(path)
    with s.connection() as c:c.execute('DELETE FROM assignments')
    with pytest.raises(PermissionError):s.import_selection(t['one'],[candidate],[],1,['one','two'])
    with pytest.raises(ValueError):s.import_selection(t['admin'],[candidate],[EXAM],1,['one','two'])
    assert s.dashboard(t['one'])['cases']==[]
    with pytest.raises(ValueError):s.import_selection(t['admin'],[{**candidate,'input_sha256':'b'*64}],[],1,['one','two'])
    result=s.import_selection(t['admin'],[candidate],[],1,['one','two'])
    with pytest.raises(ReviewConflict):s.import_selection(t['admin'],[candidate],[],1,['one','two'])
    with pytest.raises(ValueError,match='minutes'):s.submit(t['one'],EXAM,p,mask.to_bytes())
    a=s.submit(t['one'],EXAM,{**p,'annotation_minutes':12.5},mask.to_bytes())
    b=s.submit(t['two'],EXAM,{**p,'annotation_minutes':10},mask.to_bytes())
    s.adjudicate(t['judge'],EXAM,[a['id'],b['id']],'approve',a['id'],'Reviewed')
    progress=s.selection_status(t['admin'])[0]['progress'][0]
    assert progress['reported_annotation_minutes']==22.5 and progress['effort_reports']==2
    export=s.export(t['admin'],[EXAM])
    with zipfile.ZipFile(BytesIO(s.download_export(t['admin'],export['export_id']))) as z:
        row=json.loads(z.read('manifest.json'))['records'][0]
        assert row['active_learning']['batch']==result['batch_id']
    path.write_text('{}')
    with pytest.raises(ValueError,match='partitions changed'):s.import_selection(t['admin'],[candidate],[],1,['one','two'])
