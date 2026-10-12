"""Verify an offline-installed release using existing host dependencies."""
import argparse, importlib.util, json, threading, http.client
from pathlib import Path
from http.server import ThreadingHTTPServer
import neurofusion.inference as inference
from neurofusion.jobs import JobStore

p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--installed',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
project=a.project.resolve();installed=a.installed.resolve()
assert Path(inference.__file__).resolve().is_relative_to(installed), 'Not importing the installed package'
predictor=inference.Predictor(project,device='cpu')
models={key:type(predictor.model(key)).__name__ for key in inference.MODELS}
spec=importlib.util.spec_from_file_location('release_viewer',project/'scripts/serve_viewer.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.ROOT=project/'experiments/deployment-smoke'
server=ThreadingHTTPServer(('127.0.0.1',0),module.Handler)
server.jobs=JobStore(module.ROOT,predictor)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
checks={}
try:
    for path,expected in [('/api/health',200),('/',200),('/pyproject.toml',404),('/experiments/tumor-cnn-002/last.pt',404)]:
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        connection.request('GET',path);response=connection.getresponse();response.read()
        checks[path]=response.status==expected;connection.close()
finally:
    server.shutdown();server.server_close();thread.join()
result={'passed':all(checks.values()),'installed_import':str(inference.__file__),'models_loaded':models,'http_checks':checks,
        'scope':'Offline fresh-directory installation on existing laptop dependencies; loopback HTTP; not clean-machine or public hosting verification'}
with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
if not result['passed']:raise SystemExit(1)
