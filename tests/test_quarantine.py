import json
from pathlib import Path
import subprocess
import sys

from neurofusion.data import build_manifest, save_json, audit
from neurofusion.demo import create_demo


def test_quarantine_preserves_source_and_excludes_both_aliases(tmp_path):
    root=tmp_path/'data'
    index=create_demo(root)
    manifest=build_manifest(index,root,'synthetic-only')
    manifest['studies'][1]['files']['dwi']=manifest['studies'][0]['files']['dwi'].copy()
    source=tmp_path/'source.json'
    save_json(source,manifest)
    before=source.read_bytes()
    script=Path(__file__).resolve().parents[1]/'scripts/quarantine_duplicates.py'
    output=tmp_path/'curated'
    result=subprocess.run([sys.executable,str(script),'--manifest',str(source),'--output',str(output)],capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    retained=json.loads((output/'manifest.json').read_text())
    splits=json.loads((output/'draft-splits.json').read_text())
    assert len(retained['studies'])==10
    assert set(retained['curation']['excluded_subjects'])=={'synthetic-000','synthetic-001'}
    assert audit(retained,splits)['passed']
    assert source.read_bytes()==before
