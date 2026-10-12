import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image


def test_curation_quarantines_test_overlap_and_conflicting_labels(tmp_path):
    root=tmp_path/'raw'; root.mkdir()
    audit=tmp_path/'audit'; audit.mkdir()
    (root/'manifest.json').write_text('[]')
    a=np.random.default_rng(1).integers(0,256,(32,32,3),dtype=np.uint8)
    b=np.random.default_rng(2).integers(0,256,(32,32,3),dtype=np.uint8)
    rows=[]
    for name,split,label,values in [('a','train','glioma',a),('b','test','glioma',a),
                                   ('c','train','glioma',b),('d','train','pituitary',b)]:
        path=root/f'{name}.png'; Image.fromarray(values).save(path)
        rows.append({'task':'classification','path':path.name,'source_split':split,'label':label,
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'pixel_sha256':hashlib.sha256(values.tobytes()).hexdigest()})
    (audit/'manifest.json').write_text(json.dumps({'files':rows}))
    script=Path(__file__).parents[1]/'scripts/curate_brisc.py'
    out=tmp_path/'curated'
    subprocess.run([sys.executable,str(script),'--root',str(root),'--audit',str(audit),'--output',str(out)],check=True,capture_output=True)
    result=json.loads((out/'splits.json').read_text())
    by_name={r['path']:r for r in result['assignments']}
    assert by_name['a.png']['partition']=='quarantine'
    assert by_name['b.png']['partition']=='test'
    assert by_name['c.png']['reason']==by_name['d.png']['reason']=='label_conflict'
    assert by_name['c.png']['partition']==by_name['d.png']['partition']=='quarantine'
