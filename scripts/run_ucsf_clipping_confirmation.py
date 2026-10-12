from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-clipping-confirmation-001';out.mkdir(exist_ok=False)
(out/'protocol.json').write_bytes((root/'configs/ucsf_clipping_confirmation_protocol.json').read_bytes())
(out/'training-runner.py').write_bytes((root/'scripts/train_ucsf_specialist.py').read_bytes())
for seed in (42,43,44):
 name=f'ucsf-clipping-seed{seed}-001';print(f'Starting seed {seed}',flush=True)
 with (out/f'seed-{seed}.log').open('w',encoding='utf-8') as log:
  subprocess.run([sys.executable,str(root/'scripts/train_ucsf_specialist.py'),'--clip-grad','--seed',str(seed),'--output',str(root/'experiments'/name)],stdout=log,stderr=subprocess.STDOUT,cwd=root,check=True)
 s=json.loads((root/'experiments'/name/'summary.json').read_text());print(f'Seed {seed} final Dice {s["final_epoch"]["aggregate"]["dice"]["mean"]:.6f}',flush=True)
 subprocess.run([sys.executable,str(root/'scripts/verify_ucsf_checkpoint.py'),'--run','experiments/'+name],cwd=root,check=True)
print('Three full training runs and checkpoint reloads completed.',flush=True)
