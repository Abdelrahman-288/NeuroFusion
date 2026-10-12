import json
from io import BytesIO
import nibabel as nib
import numpy as np
from PIL import Image
import pytest
from neurofusion.cohort_review import CohortReview, ReviewConflict
from neurofusion.external_import import digest


@pytest.fixture
def workbench(tmp_path):
    acq=tmp_path/'acquisition';acq.mkdir()
    exam='UCSF-PDGM-0001';files=[]
    for role,suffix in enumerate(('T1c','tumor_segmentation')):
        data=np.arange(120,dtype=np.float32).reshape(4,5,6) if role==0 else np.zeros((4,5,6),dtype=np.float32)
        if role:data[1,2,3]=4
        volume=nib.Nifti1Image(data,np.diag([1.,2.,3.,1.]))
        volume.header.set_xyzt_units('mm');p=acq/f'{exam}_{suffix}.nii.gz';nib.save(volume,p)
        files.append({'path':p.name,'sha256':digest(p)})
    (acq/'summary.json').write_text(json.dumps({'results':[{'exam_id':exam,'patient_id':exam,'status':'integrity_verified','files':files}]}))
    return CohortReview(acq,tmp_path/'reviews'),exam


def payload(store,exam):
    d=store.details(exam)
    return dict(expected_revision=0,manifest_sha256=d['manifest_sha256'],image_sha256=d['image_sha256'],
                mask_sha256=d['mask_sha256'],reviewer_name='Synthetic tester',reviewer_qualification='Fixture only',
                reviewed_at='2026-10-09T12:00:00+03:00',notes='Synthetic test; not a human review',
                decision='accept',whole_volume_reviewed=True,identity_checked=True,orientation_checked=True,alignment_checked=True)


def test_every_plane_and_end_slice_and_overlay(workbench):
    store,exam=workbench;d=store.details(exam)
    assert d['shape']==[4,5,6] and d['spacing_mm']==[1,2,3]
    for axis,size in enumerate(d['shape']):
        for index in (0,size-1):
            img=Image.open(BytesIO(store.slice_png(exam,axis,index,False)))
            other=[d['shape'][i] for i in range(3) if i!=axis]
            assert img.size==tuple(other)
    base=np.array(Image.open(BytesIO(store.slice_png(exam,2,3,False))))
    overlay=np.array(Image.open(BytesIO(store.slice_png(exam,2,3,True))))
    assert np.any(base!=overlay)
    assert len(store.history(exam)['reviews'])==0


@pytest.mark.parametrize('axis,index,overlay',[(3,0,True),(0,-1,True),(0,4,True),(True,0,True),(0,1,1)])
def test_invalid_slice_rejected(workbench,axis,index,overlay):
    store,exam=workbench
    with pytest.raises(ValueError):store.slice_png(exam,axis,index,overlay)


def test_source_changes_invalidate_cached_volume_and_submission(workbench):
    store,exam=workbench;p=payload(store,exam)
    source=store.acquisition/store.records[exam]['files'][0]['path']
    source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):store.slice_png(exam,0,0,False)
    with pytest.raises(ValueError,match='checksum'):store.submit(exam,p)


def test_append_only_reviews_and_conflicts_survive_restart(workbench):
    store,exam=workbench;p=payload(store,exam);first=store.submit(exam,p)
    with pytest.raises(ReviewConflict):store.submit(exam,p)
    p.update(expected_revision=1,decision='needs_followup',notes='Correction')
    store.submit(exam,p)
    reopened=CohortReview(store.acquisition,store.storage)
    h=reopened.history(exam)
    assert h['revision']==2 and h['reviews'][0]==first and not h['qualification_promoted']


def test_missing_full_review_or_wrong_hash_never_saved(workbench):
    store,exam=workbench;p=payload(store,exam)
    p['whole_volume_reviewed']=False
    with pytest.raises(ValueError):store.submit(exam,p)
    p['whole_volume_reviewed']=True;p['mask_sha256']='f'*64
    with pytest.raises(ReviewConflict):store.submit(exam,p)
    assert store.history(exam)['revision']==0


def test_unknown_case_and_manifest_path_escape_rejected(workbench):
    store,exam=workbench
    with pytest.raises(ValueError):store.details('../'+exam)
    path=store.acquisition/'summary.json';m=json.loads(path.read_text())
    m['results'][0]['files'][0]['path']='../'+m['results'][0]['files'][0]['path']
    path.write_text(json.dumps(m))
    with pytest.raises(ValueError):CohortReview(store.acquisition,store.storage)


def test_http_review_flow_and_same_origin_boundaries(workbench):
    import http.client
    import importlib.util
    from pathlib import Path
    from http.server import ThreadingHTTPServer
    import threading
    store,exam=workbench
    spec=importlib.util.spec_from_file_location('review_http_test',Path(__file__).resolve().parents[1]/'scripts/serve_viewer.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler);server.cohort_review=store
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def request(method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        conn.request(method,path,body,headers or {});r=conn.getresponse();data=r.read();conn.close()
        return r.status,data
    try:
        assert request('GET','/cohort-review')[0]==200
        assert request('GET','/api/cohort-review')[0]==200
        assert request('GET',f'/api/cohort-review/{exam}/slice?axis=2&index=0')[1].startswith(b'\x89PNG')
        assert request('GET',f'/api/cohort-review/{exam}/slice?axis=2&index=999')[0]==400
        p=json.dumps(payload(store,exam)).encode()
        route=f'/api/cohort-review/{exam}'
        assert request('POST',route,p)[0]==403
        assert request('POST',route,p,{'X-NeuroFusion-Request':'1','Origin':'https://example.org'})[0]==403
        assert request('POST',route,p,{'X-NeuroFusion-Request':'1'})[0]==201
        assert request('POST',route,p,{'X-NeuroFusion-Request':'1'})[0]==409
        history=json.loads(request('GET',route+'/history')[1]);assert history['revision']==1
        assert request('GET',route+'/raw')[0]==404
    finally:
        server.shutdown();server.server_close();worker.join()
