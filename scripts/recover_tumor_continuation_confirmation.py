"""Execute prospectively recorded paired-seed tumor continuation experiments."""
import subprocess
import sys
from pathlib import Path
import json
from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.model_quality import compare_tumor

root=Path(__file__).resolve().parents[1];out=root/'experiments/tumor-continuation-confirmation-001'
protocol=json.loads((out/'protocol.json').read_text())
if digest(root/'scripts/train_tumor_segmentation.py')!=protocol['runner_sha256']:raise ValueError('Runner changed')
results=[]
for seed in (43,44):
    first=f'experiments/tumor-seg-seed{seed}-005'+('-recovery' if seed==43 else '')
    recovery='experiments/tumor-seg-seed43-005/last.pt' if seed==43 else None
    final=f'experiments/tumor-seg-seed{seed}-010'
    for run,epochs,resume in ((first,5,recovery),(final,10,first+'/last.pt')):
        command=[sys.executable,'scripts/train_tumor_segmentation.py','--root','data/raw/brisc-v6/brisc2025',
                 '--splits','experiments/brisc-curated-001/splits.json','--output',run,'--epochs',str(epochs),'--seed',str(seed)]
        if resume:command+=['--resume',resume]
        with (out/f'seed{seed}-epoch{epochs}-recovery.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(f'Seed {seed}: epoch {epochs} training complete',flush=True)
        with (out/f'seed{seed}-epoch{epochs}-audit.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,'scripts/report_tumor_segmentation.py','--run',run],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (out/f'seed{seed}-reproduction.log').open('w',encoding='utf-8') as log:
        subprocess.run([sys.executable,'scripts/verify_quality_checkpoints.py','--task','tumor','--run',final],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    result=compare_tumor(json.loads((root/first/'validation.json').read_text()),json.loads((root/final/'validation.json').read_text()))
    results.append({'seed':seed,**result});save_json(out/'new-seed-results.json',results)
    print(json.dumps({'seed':seed,'passed':result['development_screen_passed'],'checks':result['checks']}),flush=True)
