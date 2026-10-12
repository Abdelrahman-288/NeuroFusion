import json
from PIL import Image
import pytest
from neurofusion.jobs import JobStore
from neurofusion.reports import snapshot, render_html


class Predictor:
    def analyze(self, path, task, output):
        output.mkdir(parents=True)
        Image.new('RGB',(32,32)).save(output/'image.png')
        Image.new('RGBA',(32,32)).save(output/'overlay.png')
        (output/'result.json').write_text(json.dumps({'task':task,'views':[{'image':'image.png','overlay':'overlay.png'}],
            'models':{'test_model':'a'*64},'limitations':['<unsafe>'], 'predicted_pixels_or_voxels':0,'threshold':0.5}))


def setup(root):
    store=JobStore(root,Predictor())
    job=store.submit(b'x','tumor-image','<scan>.png','.png')['id']
    store.run_one()
    return store,job


def test_offline_report_escapes_text_and_preserves_output(tmp_path):
    store,job=setup(tmp_path)
    path=tmp_path/'results'/job/'result.json'; before=path.read_bytes()
    store.add_review(job,{'reviewer':'QA','assessment':'uncertain','note':'<script>alert(1)</script>', 'slice_index':0})
    report=snapshot(store,job); html=render_html(store,report).decode()
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '&lt;scan&gt;' in html and '&lt;unsafe&gt;' in html
    assert 'data:image/png;base64,' in html and 'src="http' not in html
    assert 'a'*64 in html and 'not a physical volume' in html
    assert report['human_review']['reviews'][0]['matches_exported_result']
    assert path.read_bytes()==before


def test_snapshot_stays_fixed_after_new_review(tmp_path):
    store,job=setup(tmp_path)
    first=snapshot(store,job)
    store.add_review(job,{'reviewer':'QA','assessment':'reviewed','note':'New note','slice_index':None})
    assert first['human_review']['reviews']==[]
    assert len(snapshot(store,job)['human_review']['reviews'])==1
    assert 'No review entries' in render_html(store,first).decode()


def test_hash_mismatch_is_explicit(tmp_path):
    store,job=setup(tmp_path)
    store.add_review(job,{'reviewer':'QA','assessment':'uncertain','note':'Old result','slice_index':0})
    path=tmp_path/'results'/job/'result.json'; path.write_text(path.read_text()+'\n')
    report=snapshot(store,job)
    assert not report['human_review']['reviews'][0]['matches_exported_result']
    assert 'different result JSON hash' in render_html(store,report).decode()


def test_preview_cannot_escape_result_directory(tmp_path):
    store,job=setup(tmp_path)
    report=snapshot(store,job); report['model_output']['views'][0]['image']='../../private.png'
    with pytest.raises(ValueError): render_html(store,report)


def test_report_requires_completed_job(tmp_path):
    store=JobStore(tmp_path,Predictor())
    job=store.submit(b'x','stroke-dwi','x.nii','.nii')['id']
    with pytest.raises(ValueError): snapshot(store,job)
    with pytest.raises(ValueError): snapshot(store,'../result')


def test_uncertainty_decision_preserved_and_escaped(tmp_path):
    store,job=setup(tmp_path)
    path=tmp_path/'results'/job/'result.json'
    result=json.loads(path.read_text())
    result['uncertainty']={'decision':'abstain','reason':'Unqualified <input>',
        'classification_development_screen':{'decision':'withhold'}}
    path.write_text(json.dumps(result))
    report=snapshot(store,job)
    assert report['model_output']['uncertainty']==result['uncertainty']
    html=render_html(store,report).decode()
    assert 'Uncertainty decision: abstain' in html
    assert 'Unqualified &lt;input&gt;' in html and 'Unqualified <input>' not in html
    assert 'Classification development screen: withhold' in html


def test_legacy_result_has_no_implied_reliability(tmp_path):
    store,job=setup(tmp_path)
    assert 'Uncertainty decision was not recorded' in render_html(store,snapshot(store,job)).decode()


def test_finding_links_in_report_and_changed_evidence_rejected(tmp_path):
    import numpy as np
    from neurofusion.inference import Predictor as ImageWriter
    from neurofusion.measurements import measure_regions,bind_evidence
    store,job=setup(tmp_path);folder=tmp_path/'results'/job
    result=json.loads((folder/'result.json').read_text());result.update(input_sha256='a'*64,probability_file='probability.npz',views=[])
    p=np.zeros((32,32),dtype=np.float32);p[2:5,3:6]=.9
    np.savez_compressed(folder/'probability.npz',probability=p)
    ImageWriter.view(folder,np.zeros((32,32,3),dtype=np.uint8),p>=.5,0,result)
    result['measurements']=bind_evidence(measure_regions(p),result,folder)
    (folder/'result.json').write_text(json.dumps(result))
    report=snapshot(store,job);html=render_html(store,report).decode()
    assert 'href="#preview-0"' in html and 'id="preview-0"' in html
    assert '9 pixels' in html and 'Physical area/volume unavailable' in html
    (folder/'overlay-000.png').write_bytes(b'changed')
    with pytest.raises(ValueError):render_html(store,report)
