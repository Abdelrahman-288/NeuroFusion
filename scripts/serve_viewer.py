"""Loopback-only local model viewer; serves only static UI and generated results."""
import argparse
import json
import mimetypes
import socket
import re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from neurofusion.jobs import JobStore
from urllib.parse import urlparse,parse_qs,unquote
from neurofusion.inference import Predictor
from neurofusion.reports import snapshot, render_html
from neurofusion.cohort_review import CohortReview, ReviewConflict

PROJECT=Path(__file__).resolve().parents[1]
ROOT=PROJECT/'experiments/local-viewer'

PILOT_REPORTS={
    'exposure':('ucsf-exposure-001',{'index.html','summary.json','exposure-ledger.json','review-template.json','scan-inventory.json','provenance.json','verification.json'}),
    'acquisition':('ucsf-acquisition-001',{'index.html','summary.json','provenance.json','verification.json','qualification.json'}),
    'qualification':('ucsf-qualification-001',{'index.html','summary.json','acquisition-queue.json','provenance.json','verification.json'}),
    'clipping-confirmation':('ucsf-clipping-confirmation-001',{'index.html','summary.json','protocol.json','provenance.json','verification.json'}),
    'clipping':('ucsf-gradient-clip-probe-002',{'index.html','summary.json','evaluation.json','intervention-protocol.json','provenance.json','verification.json'}),
    'replay':('ucsf-epoch-replay-001',{'index.html','summary.json','analysis.json','protocol.json','provenance.json','verification.json'}),
    'diagnostics':('ucsf-training-diagnostics-001',{'index.html','summary.json','results.json','protocol.json','provenance.json','verification.json'}),
    'confirmation':('ucsf-lr-confirmation-001',{'index.html','summary.json','protocol.json','provenance.json','verification.json'}),
    'learning-rate':('ucsf-low-lr-comparison-001',{'index.html','summary.json','protocol.json','provenance.json','verification.json'}),
    'sampling':('ucsf-balanced-comparison-001',{'index.html','summary.json','protocol.json','provenance.json','verification.json'}),
    'specialist':('ucsf-specialist-train-002',{'index.html','summary.json','history.json','protocol.json','provenance.json','verification.json'}),
    'errors':('ucsf-specialist-errors-001',{'index.html','summary.json','provenance.json','verification.json'}),
    'pilot':('pdgm-import-004',{'index.html','summary.json','download-provenance.json'}),
    'resolution':('pdgm-pilot-resolution-001',{'index.html','summary.json','protocol.json','alignment-review.json'}),
    'targets':('pdgm-target-contract-001',{'index.html','summary.json','contract.json'}),
    'separation':('pdgm-cohort-separation-001',{'index.html','summary.json','candidate-inventory.json'}),
    'alignment':('pdgm-alignment-gallery-001',{'index.html','summary.json','verification.json'}),
}


def pilot_report_path(route):
    parts=route.split('/',4)
    if len(parts)!=5 or parts[3] not in PILOT_REPORTS:
        return None
    key,name=parts[3],parts[4]
    directory,allowed=PILOT_REPORTS[key]
    permitted=name in allowed
    if key=='resolution':
        permitted |= bool(re.fullmatch(r'case-(?:0[1-9]|1[0-9]|20)/summary\.json',name))
    if key=='alignment':
        permitted |= bool(re.fullmatch(r'case-(?:0[1-9]|1[0-9]|20)/[012]-[0-9]{1,3}(?:-mask)?\.png',name))
    if key=='errors':
        permitted |= bool(re.fullmatch(r'UCSF-PDGM-(?:0038|0172|0194|0274)/[012]-[0-9]{1,3}(?:-overlay)?\.png',name))
    if not permitted:
        return None
    root=(PROJECT/'experiments'/directory).resolve()
    path=(root/name).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


class Handler(BaseHTTPRequestHandler):
    def send(self,status,body,kind='application/json',filename=None):
        if isinstance(body,dict): body=json.dumps(body).encode()
        self.send_response(status); self.send_header('Content-Type',kind)
        if status>=400:self.send_header('Connection','close')
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(body)
        if status>=400:
            # An early POST rejection can leave inbound bytes unread. Closing the
            # socket immediately can reset it on Windows before the client sees
            # our response. Send FIN first, then drain a bounded amount of data.
            self.close_connection=True
            self.wfile.flush()
            try:
                self.connection.shutdown(socket.SHUT_WR)
                self.connection.settimeout(0.2)
                remaining=65536
                while remaining:
                    chunk=self.connection.recv(min(8192,remaining))
                    if not chunk:break
                    remaining-=len(chunk)
            except OSError:
                pass

    def valid_host(self):
        return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'

    def do_GET(self):
        if not self.valid_host(): return self.send(403,{'error':'Use the displayed loopback URL'})
        route=unquote(urlparse(self.path).path)
        if route.startswith('/research/specialists/'):
            name=route[len('/research/specialists/'):]
            if name not in {'index.html','summary.json','verification.json'}:
                return self.send(404,{'error':'Unknown specialist artifact'})
            path=PROJECT/'experiments/additional-specialists-001'/name
            if not path.is_file():return self.send(404,{'error':'Specialist artifact not yet available'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/advanced-fusion/'):
            name=route[len('/research/advanced-fusion/'):]
            if name not in {'index.html','summary.json','protocol.json','checkpoint-reproduction.json','verification.json'}:
                return self.send(404,{'error':'Unknown fusion artifact'})
            path=PROJECT/'experiments/advanced-fusion-001'/name
            if not path.is_file():return self.send(404,{'error':'Fusion artifact not yet available'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/independent/'):
            name=route[len('/research/independent/'):]
            if name not in {'index.html','summary.json','audit-protocol.json','evaluation-protocol-draft.json','verification.json','volume-comparisons.json'}:
                return self.send(404,{'error':'Unknown independence artifact'})
            path=PROJECT/'experiments/independent-evaluation-001'/name
            if not path.is_file():return self.send(404,{'error':'Independence artifact not yet available'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/model-quality/'):
            name=route[len('/research/model-quality/'):]
            if name not in {'index.html','summary.json','protocol.json','verification.json','source-provenance.json','tumor-confirmation.json','stroke-thresholds.json'}:
                return self.send(404,{'error':'Unknown quality artifact'})
            path=PROJECT/'experiments/model-quality-001'/name
            if not path.is_file():return self.send(404,{'error':'Quality artifact not yet available'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route=='/release-status':
            return self.send(200,(PROJECT/'viewer/release-status.html').read_bytes(),'text/html; charset=utf-8')
        if route=='/api/release-status':
            return self.send(200,(PROJECT/'docs/release_status.json').read_bytes(),'application/json')
        if route=='/cohort-review':
            return self.send(200,(PROJECT/'viewer/cohort-review.html').read_bytes(),'text/html; charset=utf-8')
        if route=='/api/cohort-review' or route.startswith('/api/cohort-review/'):
            workbench=getattr(self.server,'cohort_review',None)
            if workbench is None:return self.send(503,{'error':'Cohort review is unavailable'})
            try:
                if route=='/api/cohort-review':return self.send(200,workbench.cases())
                parts=route.split('/')
                if len(parts)==4:return self.send(200,workbench.details(parts[3]))
                if len(parts)==5 and parts[4]=='history':return self.send(200,workbench.history(parts[3]))
                if len(parts)==5 and parts[4]=='slice':
                    query=parse_qs(urlparse(self.path).query)
                    axis=int(query.get('axis',[''])[0]);index=int(query.get('index',[''])[0])
                    overlay=query.get('overlay',['1'])[0]
                    if overlay not in ('0','1'):raise ValueError('Invalid overlay')
                    return self.send(200,workbench.slice_png(parts[3],axis,index,overlay=='1'),'image/png')
                return self.send(404,{'error':'Unknown cohort review route'})
            except (ValueError,OSError,KeyError) as error:return self.send(400,{'error':str(error)})
        if route.startswith('/research/ucsf/'):
            path=pilot_report_path(route)
            if path is None:return self.send(404,{'error':'Research artifact unavailable'})
            kind='text/html; charset=utf-8' if path.suffix=='.html' else 'image/png' if path.suffix=='.png' else 'application/json'
            return self.send(200,path.read_bytes(),kind)
        if route.startswith('/research/adapter/'):
            name=route[len('/research/adapter/'):]
            if name not in ('index.html','summary.json','synthetic-preview.png'):return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/external-adapter-001'/name
            if not path.is_file():return self.send(404,{'error':'Adapter verification unavailable'})
            kind='image/png' if name.endswith('.png') else 'text/html; charset=utf-8' if name=='index.html' else 'application/json'
            return self.send(200,path.read_bytes(),kind)
        if route.startswith('/research/pdgm/'):
            name=route[len('/research/pdgm/'):]
            if name not in ('index.html','summary.json'):return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/pdgm-intake-001'/name
            if not path.is_file():return self.send(404,{'error':'Intake report unavailable'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/overlap/'):
            name=route[len('/research/overlap/'):]
            if name not in ('index.html','summary.json'):return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/external-overlap-001'/name
            if not path.is_file():return self.send(404,{'error':'Audit unavailable'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/contrast/'):
            name=route[len('/research/contrast/'):]
            if name not in ('index.html','summary.json','protocol.json'):return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/contrast-multiseed-001'/name
            if not path.is_file():return self.send(404,{'error':'Evaluation unavailable'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/multiseed/'):
            name=route[len('/research/multiseed/'):]
            if name not in ('index.html','summary.json','protocol.json'):return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/multiseed-001'/name
            if not path.is_file():return self.send(404,{'error':'Evaluation unavailable'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/augmentation/'):
            name=route[len('/research/augmentation/'):]
            if name not in ('index.html','summary.json'): return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/augmentation-comparison-001'/name
            if not path.is_file(): return self.send(404,{'error':'Comparison unavailable'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route.startswith('/research/robustness/'):
            name=route[len('/research/robustness/'):]
            if name not in ('index.html','summary.json','coverage.json','config.json'):
                return self.send(404,{'error':'Not found'})
            path=PROJECT/'experiments/robustness-tumor-001'/name
            if not path.is_file(): return self.send(404,{'error':'Evaluation has not been run on this computer'})
            return self.send(200,path.read_bytes(),'text/html; charset=utf-8' if name=='index.html' else 'application/json')
        if route=='/api/health': return self.send(200,{'app':'NeuroFusion local viewer','version':5})
        if route.startswith('/api/reports/'):
            query=parse_qs(urlparse(self.path).query)
            fmt=query.get('format',['html'])[0]
            if fmt not in ('html','json'): return self.send(400,{'error':'Choose html or json'})
            try:
                report=snapshot(self.server.jobs,route.split('/')[-1])
                body=render_html(self.server.jobs,report) if fmt=='html' else report
                filename=f'neurofusion-{report["job"]["id"]}.{fmt}' if query.get('download')==['1'] else None
                return self.send(200,body,'text/html; charset=utf-8' if fmt=='html' else 'application/json',filename)
            except (ValueError, OSError, KeyError):
                return self.send(404,{'error':'Completed report assets are unavailable or invalid'})
        if route.startswith('/api/reviews/'):
            try: return self.send(200,self.server.jobs.reviews(route.split('/')[-1]))
            except ValueError as error: return self.send(404,{'error':str(error)})
        if route=='/api/jobs': return self.send(200,{'jobs':self.server.jobs.history()})
        if route.startswith('/api/jobs/'):
            job=self.server.jobs.get(route.split('/')[-1])
            return self.send(200,job) if job else self.send(404,{'error':'Not found'})
        if route=='/': return self.send(200,(PROJECT/'viewer/index.html').read_bytes(),'text/html; charset=utf-8')
        if route.startswith('/results/'):
            parts=route[len('/results/'):].split('/')
            if len(parts)!=2 or len(parts[0])!=32 or any(c not in '0123456789abcdef' for c in parts[0]):
                return self.send(404,{'error':'Not found'})
            job=self.server.jobs.get(parts[0])
            if not job or job['status']!='completed': return self.send(404,{'error':'Result not complete'})
            folder=(ROOT/'results'/parts[0]).resolve(); path=(folder/parts[1]).resolve()
            if path.parent!=folder or not path.is_file() or path.suffix not in ['.png','.json','.npz','.gz']:
                return self.send(404,{'error':'Not found'})
            return self.send(200,path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        return self.send(404,{'error':'Not found'})

    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.valid_host() or (origin and origin!=f'http://127.0.0.1:{self.server.server_port}'):
            return self.send(403,{'error':'Local same-origin requests only'})
        if self.headers.get('X-NeuroFusion-Request')!='1': return self.send(403,{'error':'Missing request header'})
        parsed=urlparse(self.path)
        if parsed.path.startswith('/api/cohort-review/'):
            workbench=getattr(self.server,'cohort_review',None)
            if workbench is None:return self.send(503,{'error':'Cohort review is unavailable'})
            try:
                parts=parsed.path.split('/')
                if len(parts)!=4:return self.send(404,{'error':'Unknown cohort review route'})
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=20000:return self.send(413,{'error':'Review limit is 20000 bytes'})
                self.connection.settimeout(15)
                body=self.rfile.read(size)
                if len(body)!=size:raise ValueError('Incomplete review')
                return self.send(201,{'review':workbench.submit(parts[3],json.loads(body))})
            except ReviewConflict as error:return self.send(409,{'error':str(error)})
            except (ValueError,OSError,KeyError) as error:return self.send(400,{'error':str(error)})
        if parsed.path.startswith('/api/reviews/'):
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=20000: return self.send(413,{'error':'Review limit is 20000 bytes'})
                self.connection.settimeout(15)
                body=self.rfile.read(size)
                if len(body)!=size: raise ValueError('Incomplete review')
                entry=self.server.jobs.add_review(parsed.path.split('/')[-1],json.loads(body))
                return self.send(201,{'review':entry})
            except (ValueError, OSError) as error:
                return self.send(400,{'error':str(error)})
        if parsed.path!='/api/analyze': return self.send(404,{'error':'Not found'})
        query=parse_qs(parsed.query); task=query.get('task',[''])[0]; name=query.get('filename',[''])[0].lower()
        suffix='.nii.gz' if name.endswith('.nii.gz') else Path(name).suffix
        allowed={'tumor-image':{'.png','.jpg','.jpeg'},'stroke-dwi':{'.nii','.nii.gz'}}
        if task not in allowed or suffix not in allowed[task]: return self.send(400,{'error':'Choose a task-compatible file'})
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError: return self.send(400,{'error':'Invalid upload length'})
        if not 0<size<=25*1024*1024: return self.send(413,{'error':'Upload limit is 25 MiB'})
        try:
            self.connection.settimeout(120)
            body=self.rfile.read(size)
            if len(body)!=size: return self.send(400,{'error':'Incomplete upload'})
            job=self.server.jobs.submit(body,task,name,suffix)
            self.send(202,{'job':job})
        except (ValueError,OSError,RuntimeError) as error:
            self.send(400,{'error':str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            self.send(500,{'error':'Analysis failed. Check the local server log; no result was accepted.'})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--port',type=int,default=8766); args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.jobs=JobStore(ROOT,Predictor(PROJECT))
    acquisition=PROJECT/'experiments/ucsf-acquisition-001'
    server.cohort_review=CohortReview(acquisition,ROOT/'cohort-review') if (acquisition/'summary.json').exists() else None
    server.jobs.start()
    print(f'NeuroFusion local viewer: http://127.0.0.1:{args.port}',flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        server.jobs.close()
