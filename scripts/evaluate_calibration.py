"""Fit on half the validation groups; describe the remaining groups under all stresses."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import numpy as np
from neurofusion.calibration import group_partition,fit_temperature,scale,metrics
from neurofusion.data import save_json
from neurofusion.robustness import CONDITIONS


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use fresh output')
    base=Path('experiments/robustness-tumor-001')
    split_path=Path('experiments/brisc-curated-001/splits.json')
    checkpoint=Path('experiments/tumor-cnn-002/last.pt')
    config=json.loads((base/'config.json').read_text())
    coverage=json.loads((base/'coverage.json').read_text())
    split=json.loads(split_path.read_text())
    if config['partition']!='validation' or config['test_loaded'] or coverage['test_loaded'] or not split['frozen']:
        raise ValueError('Frozen validation-only evidence required')
    if sha(split_path)!=config['split_sha256'] or sha(checkpoint)!=config['checkpoint_sha256']:
        raise ValueError('Reference checksum mismatch')
    expected=sorted([r for r in split['assignments'] if r['partition']=='validation'],key=lambda r:r['path'])
    rows=coverage['images']
    if len(rows)!=len(expected):raise ValueError('Coverage count mismatch')
    for actual,wanted in zip(rows,expected):
        if any(actual[k]!=wanted[k] for k in ('path','sha256','group_id','label')):
            raise ValueError('Coverage/order mismatch')
    classes=['glioma','meningioma','pituitary','no_tumor']
    labels=np.asarray([classes.index(r['label']) for r in rows])
    groups=[r['group_id'] for r in rows]
    fit=group_partition(groups);evaluation=~fit
    args.output.mkdir(parents=True)
    protocol={'method':'Temperature scaling on clipped log probabilities (floor 1e-12)',
        'fit':'Clean predictions, half of validation similarity groups sorted by SHA256(calibration-v1:group_id)',
        'objective':'Image-weighted negative log likelihood; temperature bounded 0.05 to 20',
        'bins':10,'checkpoint_sha256':sha(checkpoint),'split_sha256':sha(split_path),
        'conditions':list(CONDITIONS),'automatic_promotion':False,
        'limitation':'Development only: validation data was used in earlier model development; groups are not verified patients.'}
    save_json(args.output/'protocol.json',protocol)
    save_json(args.output/'partition.json',{'records':[{'path':r['path'],'group_id':r['group_id'],
        'role':'temperature_fit' if f else 'calibration_evaluation'} for r,f in zip(rows,fit)]})
    with np.load(base/'clean.npz') as data:
        if not np.array_equal(data['labels'],labels):raise ValueError('Clean labels mismatch')
        temperature=fit_temperature(data['probabilities'][fit],labels[fit])
    results={}
    for condition in CONDITIONS:
        with np.load(base/f'{condition}.npz') as data:
            if not np.array_equal(data['labels'],labels):raise ValueError('Stress labels mismatch')
            original=data['probabilities'][evaluation]
        calibrated=scale(original,temperature)
        if not np.array_equal(original.argmax(1),calibrated.argmax(1)):
            raise ValueError('Temperature unexpectedly changed predicted classes')
        results[condition]={'before':metrics(original,labels[evaluation]),'after':metrics(calibrated,labels[evaluation])}
        np.savez_compressed(args.output/f'{condition}.npz',original=original,calibrated=calibrated,labels=labels[evaluation])
    summary={'temperature':temperature,'fit_images':int(fit.sum()),'evaluation_images':int(evaluation.sum()),
        'fit_groups':len(set(np.asarray(groups)[fit])),'evaluation_groups':len(set(np.asarray(groups)[evaluation])),
        'test_scored':False,'viewer_model_changed':False,'external_validation':False,'conditions':results}
    save_json(args.output/'summary.json',summary)
    sources=[split_path,checkpoint,base/'coverage.json',base/'config.json',Path(__file__),Path('src/neurofusion/calibration.py')]+[base/f'{c}.npz' for c in CONDITIONS]
    save_json(args.output/'source-hashes.json',{str(p):sha(p) for p in sources})
    table=''.join(f'<tr><td>{html.escape(c)}</td><td>{r["before"]["accuracy"]:.3f}</td><td>{r["before"]["nll"]:.3f} → {r["after"]["nll"]:.3f}</td><td>{r["before"]["ece_10_equal_width"]:.3f} → {r["after"]["ece_10_equal_width"]:.3f}</td></tr>' for c,r in results.items())
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Confidence calibration</title><style>body{font:18px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#101827;color:#e6edf6}td,th{padding:12px;text-align:left}a{color:#71d6ee}</style><h1>Development confidence calibration</h1><p>Separate similarity groups for fitting and evaluation. Not independent patients or external validation. Viewer unchanged.</p>'
        +f'<p>Temperature: {temperature:.4f}. Fit images: {fit.sum()}; evaluation images: {evaluation.sum()}.</p>'
        +'<table><tr><th>Condition</th><th>Accuracy (unchanged)</th><th>NLL before → after</th><th>ECE before → after</th></tr>'+table+'</table><p>Lower NLL/ECE is better. Improved confidence metrics do not repair wrong predictions or guarantee reliable confidence under domain shift.</p><a href="summary.json">Full results</a>',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='conditions'},indent=2))
    for c,r in results.items():print(c,'NLL',r['before']['nll'],r['after']['nll'],'ECE',r['before']['ece_10_equal_width'],r['after']['ece_10_equal_width'])


if __name__=='__main__':main()
