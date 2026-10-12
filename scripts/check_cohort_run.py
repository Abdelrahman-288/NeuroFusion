"""Verify study coverage and checkpoint identity in a completed cohort run."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from neurofusion.data import save_json


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args()
output=args.run/'coverage-verification.json'
if output.exists():
    parser.error('Verification already exists')
config=json.loads((args.run/'config.json').read_text())
summary=json.loads((args.run/'summary.json').read_text())
history=json.loads((args.run/'history.json').read_text())
validation=json.loads((args.run/'validation.json').read_text())
checks={}
for epoch in range(1,summary['total_epochs']+1):
    counts=Counter(row['subject'] for row in history if row['epoch']==epoch)
    checks[f'epoch_{epoch}_training_coverage']=counts==Counter({s:config['patches_per_study'] for s in config['train_subjects']})
    visits=[v for v in validation if v['epoch']==epoch]
    checks[f'epoch_{epoch}_validation_coverage']=len(visits)==1 and Counter(c['subject'] for c in visits[0]['cases'])==Counter(config['validation_subjects'])
checks['disjoint_train_validation']=not (set(config['train_subjects']) & set(config['validation_subjects']))
checks['steps_match']=len(history)==summary['steps']==summary['total_epochs']*len(config['train_subjects'])*config['patches_per_study']
checks['predictions_complete']=all((args.run/'predictions'/f'{s}-probability.nii.gz').exists() for s in config['validation_subjects'])
checks['holdout_disabled']=config['holdout_evaluated'] is False and summary['holdout_evaluated'] is False
report={'passed':all(checks.values()),'checks':checks,'last_checkpoint_sha256':digest(args.run/'last.pt'),
        'best_checkpoint_sha256':digest(args.run/'best.pt') if (args.run/'best.pt').exists() else None}
save_json(output,report)
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
