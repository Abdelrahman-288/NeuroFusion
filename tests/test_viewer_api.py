"""Exercise the actual HTTP handler without requiring trained models."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
import pytest
from neurofusion.jobs import JobStore


@pytest.fixture
def api(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/serve_viewer.py'
    spec = importlib.util.spec_from_file_location('viewer_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    module.PROJECT = tmp_path
    class Predictor:
        def analyze(self, path, task, output):
            output.mkdir(parents=True)
            (output / 'result.json').write_text(json.dumps({'task': task, 'views': [{}]}))
    server = ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
    server.jobs = JobStore(tmp_path, Predictor())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        conn.request(method, path, body, headers or {})
        response = conn.getresponse()
        status, data = response.status, response.read()
        conn.close()
        return status, json.loads(data)
    yield request, server.jobs
    server.shutdown(); server.server_close(); thread.join()


def test_ucsf_reports_keep_raw_files_private(api):
    request,store=api
    for key,directory in [('pilot','pdgm-import-004'),('resolution','pdgm-pilot-resolution-001'),
                          ('targets','pdgm-target-contract-001'),('separation','pdgm-cohort-separation-001'),
                          ('alignment','pdgm-alignment-gallery-001'),('exposure','ucsf-exposure-001'),
                          ('specialist','ucsf-specialist-train-002'),('errors','ucsf-specialist-errors-001'),('sampling','ucsf-balanced-comparison-001'),('learning-rate','ucsf-low-lr-comparison-001'),('confirmation','ucsf-lr-confirmation-001'),('diagnostics','ucsf-training-diagnostics-001'),('replay','ucsf-epoch-replay-001'),('clipping','ucsf-gradient-clip-probe-002'),('clipping-confirmation','ucsf-clipping-confirmation-001'),('qualification','ucsf-qualification-001'),('acquisition','ucsf-acquisition-001')]:
        root=store.root/'experiments'/directory;root.mkdir(parents=True)
        (root/'summary.json').write_text('{"evaluation_ready":false}')
        (root/'secret.json').write_text('{}')
        assert request('GET',f'/research/ucsf/{key}/summary.json')==(200,{'evaluation_ready':False})
        for name in ('secret.json','source/model.py','slices.npz','../summary.json','%2e%2e/summary.json'):
            assert request('GET',f'/research/ucsf/{key}/{name}')[0]==404
    nested=store.root/'experiments/pdgm-pilot-resolution-001/case-01';nested.mkdir()
    (nested/'summary.json').write_text('{"size":128}')
    assert request('GET','/research/ucsf/resolution/case-01/summary.json')==(200,{'size':128})
    assert request('GET','/research/ucsf/alignment/case-01/slices.npz')[0]==404
    assert request('GET','/research/ucsf/unknown/summary.json')[0]==404


def test_model_quality_report_allowlist(api):
    request,store=api
    root=store.root/'experiments/model-quality-001';root.mkdir(parents=True)
    (root/'summary.json').write_text('{"promotion_permitted":false}')
    (root/'stroke-thresholds.json').write_text('{"independently_qualified":false}')
    (root/'last.pt').write_bytes(b'private')
    assert request('GET','/research/model-quality/summary.json')==(200,{'promotion_permitted':False})
    assert request('GET','/research/model-quality/stroke-thresholds.json')==(200,{'independently_qualified':False})
    for name in ('last.pt','../summary.json','%2e%2e/summary.json','predictions/a.nii.gz'):
        assert request('GET','/research/model-quality/'+name)[0]==404


def test_specialist_reports_do_not_expose_raw_eeg_or_dicom(api):
    request,store=api
    root=store.root/'experiments/additional-specialists-001';root.mkdir(parents=True)
    (root/'summary.json').write_text('{"all_specialists_complete":false}')
    assert request('GET','/research/specialists/summary.json')==(200,{'all_specialists_complete':False})
    for name in ('raw.edf','scan.dcm','../summary.json','last.pt'):
        assert request('GET','/research/specialists/'+name)[0]==404


def test_advanced_fusion_report_does_not_expose_volumes(api):
    request,store=api
    root=store.root/'experiments/advanced-fusion-001';root.mkdir(parents=True)
    (root/'summary.json').write_text('{"independent_uncertainty_reliability_established":false}')
    assert request('GET','/research/advanced-fusion/summary.json')==(200,{'independent_uncertainty_reliability_established':False})
    for name in ('last.pt','evaluation/both/a/probability.nii.gz','../summary.json'):
        assert request('GET','/research/advanced-fusion/'+name)[0]==404


def test_independence_report_preserves_pending_status_and_private_reviews(api):
    request,store=api
    root=store.root/'experiments/independent-evaluation-001';root.mkdir(parents=True)
    (root/'summary.json').write_text('{"independence_verified":false,"qualified_expert_reviews_completed":0}')
    (root/'review-snapshot.json').write_text('{"submissions":[]}')
    assert request('GET','/research/independent/summary.json')==(200,{'independence_verified':False,'qualified_expert_reviews_completed':0})
    for name in ('review-snapshot.json','source-inventory.json','../summary.json','raw/a.nii.gz'):
        assert request('GET','/research/independent/'+name)[0]==404


def test_submission_returns_queued_job_and_completed_result(api):
    request, store = api
    status, data = request('POST', '/api/analyze?task=tumor-image&filename=x.png', b'image', {'X-NeuroFusion-Request': '1'})
    assert status == 202
    job = data['job']['id']
    assert request('GET', '/api/jobs/' + job)[1]['status'] == 'queued'
    assert request('GET', '/results/' + job + '/result.json')[0] == 404
    store.run_one()
    assert request('GET', '/api/jobs')[1]['jobs'][0]['status'] == 'completed'
    assert request('GET', '/results/' + job + '/result.json') == (200, {'task': 'tumor-image', 'views': [{}]})


def test_early_post_rejections_deliver_response_without_socket_reset(api):
    request, _ = api
    for _ in range(20):
        status, body = request('POST', '/api/reviews/not-a-job', 'x'*4096)
        assert status == 403 and 'error' in body


def test_review_api_roundtrip_and_rejections(api):
    request, store = api
    job = store.submit(b'image', 'tumor-image', 'x.png', '.png')['id']
    route = '/api/reviews/' + job
    assert request('GET', route)[0] == 404
    store.run_one()
    data = json.dumps({'reviewer':'QA', 'note':'UI test only', 'assessment':'uncertain', 'slice_index':0})
    assert request('POST', route, data)[0] == 403
    headers = {'X-NeuroFusion-Request':'1', 'Content-Type':'application/json'}
    assert request('POST', route, data, dict(headers, Origin='https://example.org'))[0] == 403
    assert request('POST', route, '{invalid', headers)[0] == 400
    assert request('POST', route, '[]', headers)[0] == 400
    assert request('POST', route, data, headers)[0] == 201
    status, result = request('GET', route)
    assert status == 200 and result['reviews'][0]['note'] == 'UI test only'


def test_origin_and_request_header_checks(api):
    request, _ = api
    assert request('GET', '/api/jobs', headers={'Host': 'example.org'})[0] == 403
    assert request('POST', '/api/analyze')[0] == 403
    assert request('POST', '/api/analyze', headers={'X-NeuroFusion-Request':'1', 'Origin':'https://example.org'})[0] == 403


def test_report_json_route(api):
    request, store = api
    job = store.submit(b'image','tumor-image','x.png','.png')['id']
    route = '/api/reports/' + job + '?format=json&download=1'
    assert request('GET',route)[0] == 404
    store.run_one()
    status, data = request('GET',route)
    assert status == 200 and data['job']['id'] == job
    assert data['research_only'] and data['human_review']['reviews'] == []
    assert request('GET',route,headers={'Host':'example.org'})[0] == 403
    assert request('GET','/api/reports/'+job+'?format=exe')[0] == 400


def test_invalid_uploads_and_private_routes(api):
    request, _ = api
    headers = {'X-NeuroFusion-Request':'1'}
    assert request('POST', '/api/analyze?task=unknown&filename=x.png', b'x', headers)[0] == 400
    assert request('POST', '/api/analyze?task=tumor-image&filename=x.nii', b'x', headers)[0] == 400
    assert request('POST', '/api/analyze?task=tumor-image&filename=x.png', b'', headers)[0] == 413
    assert request('GET', '/jobs.sqlite3')[0] == 404
    assert request('GET', '/uploads/x.png')[0] == 404
    assert request('GET', '/results/' + 'a'*32 + '/%2e%2e')[0] == 404


def test_research_route_is_restricted(api):
    request,store=api
    folder=store.root/'experiments/robustness-tumor-001';folder.mkdir(parents=True)
    (folder/'summary.json').write_text('{"test_loaded":false}')
    assert request('GET','/research/robustness/summary.json')==(200,{'test_loaded':False})
    assert request('GET','/research/robustness/source/tumor.py')[0]==404
    assert request('GET','/research/robustness/../../jobs.sqlite3')[0]==404
    comparison=store.root/'experiments/augmentation-comparison-001';comparison.mkdir()
    (comparison/'summary.json').write_text('{"verified":true}')
    assert request('GET','/research/augmentation/summary.json')==(200,{'verified':True})
    assert request('GET','/research/augmentation/../../jobs.sqlite3')[0]==404
    multi=store.root/'experiments/multiseed-001';multi.mkdir()
    (multi/'protocol.json').write_text('{"seeds":[42,43,44]}')
    assert request('GET','/research/multiseed/protocol.json')==(200,{'seeds':[42,43,44]})
    assert request('GET','/research/multiseed/../../jobs.sqlite3')[0]==404
    contrast=store.root/'experiments/contrast-multiseed-001';contrast.mkdir()
    (contrast/'protocol.json').write_text('{"policy":"contrast-only"}')
    assert request('GET','/research/contrast/protocol.json')==(200,{'policy':'contrast-only'})
    assert request('GET','/research/contrast/../../jobs.sqlite3')[0]==404
    overlap=store.root/'experiments/external-overlap-001';overlap.mkdir()
    (overlap/'summary.json').write_text('{"evaluation_ready":false}')
    assert request('GET','/research/overlap/summary.json')==(200,{'evaluation_ready':False})
    assert request('GET','/research/overlap/fingerprints.json')[0]==404
    assert request('GET','/research/overlap/../../jobs.sqlite3')[0]==404
    pdgm=store.root/'experiments/pdgm-intake-001';pdgm.mkdir()
    (pdgm/'summary.json').write_text('{"patients":495}')
    assert request('GET','/research/pdgm/summary.json')==(200,{'patients':495})
    assert request('GET','/research/pdgm/patient-index.json')[0]==404
    assert request('GET','/research/pdgm/../../jobs.sqlite3')[0]==404
    adapter=store.root/'experiments/external-adapter-001';adapter.mkdir()
    (adapter/'summary.json').write_text('{"evaluation_ready":false}')
    assert request('GET','/research/adapter/summary.json')==(200,{'evaluation_ready':False})
    assert request('GET','/research/adapter/slices.npz')[0]==404
    assert request('GET','/research/adapter/../../jobs.sqlite3')[0]==404
