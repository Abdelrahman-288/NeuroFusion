"""Run the four additional predeclared paired-seed experiments serially."""
from pathlib import Path
import subprocess,sys,json,hashlib
root=Path(__file__).resolve().parents[1]
out=root/'experiments/ucsf-lr-confirmation-001';out.mkdir(exist_ok=False)
protocol=root/'configs/ucsf_lr_confirmation_protocol.json'
plan=json.loads(protocol.read_text())
if plan['seeds']!=[42,43,44] or plan['epochs']!=5:raise ValueError('Unexpected confirmation plan')
(out/'protocol.json').write_bytes(protocol.read_bytes())
(out/'runner.py').write_bytes(Path(__file__).read_bytes())
(out/'training-runner.py').write_bytes((root/'scripts/train_ucsf_specialist.py').read_bytes())
for seed in (43,44):
 for mode in ('baseline','low-lr'):
  name=f'ucsf-lr-confirm-seed{seed}-{mode}'
  cmd=[sys.executable,str(root/'scripts/train_ucsf_specialist.py'),'--seed',str(seed),'--output',str(root/'experiments'/name)]
  if mode=='low-lr':cmd.append('--low-lr')
  print(f'Starting {name}',flush=True)
  with (out/(name+'.log')).open('w',encoding='utf-8') as log:subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  result=json.loads((root/'experiments'/name/'summary.json').read_text())
  print(f'Completed {name}: final Dice {result["final_epoch"]["aggregate"]["dice"]["mean"]:.6f}',flush=True)
  subprocess.run([sys.executable,str(root/'scripts/verify_ucsf_checkpoint.py'),'--run','experiments/'+name],cwd=root,check=True)
print('All four additional runs and checkpoint reloads completed.',flush=True)
