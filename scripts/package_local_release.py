"""Package an explicit local research preview, excluding scans, accounts and results."""
import argparse
import json
from pathlib import Path
from neurofusion.release_bundle import build_bundle,restore_bundle,verify_bundle
from neurofusion.inference import MODELS
from neurofusion.model_registry import active_models, read_registry
from neurofusion.external_import import digest

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--restore',type=Path);p.add_argument('--destination',type=Path);a=p.parse_args()
    if sum(v is not None for v in (a.output,a.verify,a.restore))!=1:raise ValueError('Choose build, verify or restore')
    if a.verify:print(json.dumps(verify_bundle(a.verify)));return
    if a.restore:
        if a.destination is None:raise ValueError('Destination required')
        print(json.dumps(restore_bundle(a.restore,a.destination)));return
    files={name:ROOT/name for name in ('pyproject.toml','README.md','docs/LOCAL_RELEASE.md','docs/SCOPE_FREEZE.md','docs/release_status.json')}
    for name in ('docs/research_delivery.json','docs/research_qualification.json'):
        if (ROOT/name).is_file():files[name]=ROOT/name
    for folder,suffixes in [('src',{'.py'}),('scripts',{'.py','.ps1'}),('viewer',{'.html','.js','.css'}),('web',{'.html','.js','.css'}),('configs',{'.json'}),('tests',{'.py'}),('docs',{'.md'})]:
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in suffixes and '__pycache__' not in path.parts:files[path.relative_to(ROOT).as_posix()]=path
    registered=dict(active_models(ROOT,MODELS))
    checkpoints=set(MODELS.values()) | set(registered.values())
    for revision in read_registry(ROOT,MODELS)['revisions']:
        checkpoints.update(tuple(v) for v in revision['models'].values())
    for relative,expected in checkpoints:
        if digest(ROOT/relative)!=expected:raise ValueError('Pinned application model changed')
        files[relative]=ROOT/relative
    result=build_bundle(files,a.output)
    a.output.with_suffix('.verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
