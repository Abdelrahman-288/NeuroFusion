"""Verify and report the fixed final-epoch augmentation experiment."""
import argparse
import json
from pathlib import Path
import numpy as np
from neurofusion.cohort import digest
from neurofusion.robustness import CONDITIONS,summarize
from neurofusion.data import save_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Fresh output required')
    root=Path(__file__).resolve().parents[1]/'experiments'
    baseline=json.loads((root/'tumor-cnn-002/config.json').read_text())
    candidate=json.loads((root/'tumor-cnn-aug-001/config.json').read_text())
    for key in ['architecture','seed','epochs','batch_size','learning_rate','optimizer','split_sha256','classes']:
        if baseline[key]!=candidate[key]:raise ValueError('Control differs: '+key)
    training=json.loads((root/'tumor-cnn-aug-001/summary.json').read_text())
    if not training['completed'] or training['epochs']!=5 or training['updates']!=555 or training['test_evaluated']:
        raise ValueError('Incomplete or unexpected training')
    if digest(root/'tumor-cnn-aug-001/last.pt')!=training['last_checkpoint_sha256']:raise ValueError('Checkpoint changed')
    results={};coverage=None;protocol=None
    for label,folder in [('baseline','robustness-tumor-001'),('augmented','robustness-tumor-aug-001')]:
        directory=root/folder; c=json.loads((directory/'coverage.json').read_text())
        evaluation_config=json.loads((directory/'config.json').read_text())
        paired_protocol={k:evaluation_config[k] for k in ['seed','conditions','partition','images','groups','split_sha256','domain']}
        if protocol is not None and paired_protocol!=protocol:raise ValueError('Evaluation protocol differs')
        protocol=paired_protocol
        expected_hash=training['last_checkpoint_sha256'] if label=='augmented' else json.loads((root/'tumor-cnn-002/summary.json').read_text())['last_checkpoint_sha256']
        if evaluation_config['checkpoint_sha256']!=expected_hash:raise ValueError('Wrong evaluated checkpoint')
        if c['test_loaded'] or c['partition']!='validation':raise ValueError('Unexpected partition')
        if coverage is not None and c!=coverage:raise ValueError('Paired coverage differs')
        coverage=c
        summary=json.loads((directory/'summary.json').read_text())
        clean=np.load(directory/'clean.npz')['probabilities'];groups=[r['group_id'] for r in c['images']]
        for condition in CONDITIONS:
            with np.load(directory/(condition+'.npz')) as arrays:
                classes=['glioma','meningioma','pituitary','no_tumor']
                if not np.array_equal(arrays['labels'],[classes.index(r['label']) for r in c['images']]):raise ValueError('Reference labels differ')
                measured=summarize(arrays['labels'],arrays['probabilities'],clean,groups)
            if measured!=summary['conditions'][condition]:raise ValueError('Saved metric mismatch')
        results[label]=summary['conditions']
    comparison={name:{'baseline':results['baseline'][name],'augmented':results['augmented'][name],
        'accuracy_delta_pp':100*(results['augmented'][name]['accuracy']-results['baseline'][name]['accuracy'])} for name in CONDITIONS}
    args.output.mkdir(parents=True)
    summary={'verified':True,'conditions':comparison,'validation_images':len(coverage['images']),
        'test_loaded':False,'production_model_changed':False,'candidate_checkpoint_sha256':training['last_checkpoint_sha256'],
        'scope':'One seed, five epochs, development-only comparison. No clinical validation or automatic promotion.'}
    save_json(args.output/'summary.json',summary)
    table=''.join(f'<tr><td>{name}</td><td>{row["baseline"]["accuracy"]:.2%}</td><td>{row["augmented"]["accuracy"]:.2%}</td><td>{row["accuracy_delta_pp"]:+.2f}</td><td>{row["baseline"]["macro_f1"]:.4f}</td><td>{row["augmented"]["macro_f1"]:.4f}</td></tr>' for name,row in comparison.items())
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NeuroFusion augmentation comparison</title><style>body{{font:17px system-ui;max-width:1150px;margin:40px auto;padding:24px;color:#18364b}}h1{{color:#11665e}}td,th{{padding:12px;border-bottom:1px solid #ccc;text-align:left}}.notice{{background:#fff1ce;padding:20px}}.table{{overflow-x:auto}}</style>
<h1>Intensity-augmentation training comparison</h1><p>3,533 training images / 943 validation images / five epochs / 555 updates / same architecture and initialization seed</p>
<p class="notice">Development experiment only. Current viewer model remains unchanged. Held-out test images were not used.</p>
<div class="table"><table><tr><th>Condition</th><th>Baseline accuracy</th><th>Augmented accuracy</th><th>Change (pp)</th><th>Baseline F1</th><th>Augmented F1</th></tr>{table}</table></div>
<h2>Controlled protocol</h2><p>Both models were trained from scratch using seed 42, Adam at 0.001, batch size 32, and five epochs. Compare final epoch 5, not the best validation checkpoint. The candidate adds training-only intensity augmentation with independent RNG seed 1042. Each image has 80% probability of combined contrast (0.8–1.2 around 0.5), brightness (0.8–1.2), and Gaussian noise (sigma 0–0.03), clipped to [0,1]. Validation is unaugmented during training.</p>
<p>Stress evaluation uses exactly the six saved conditions, seed and validation ordering from the baseline evaluation. The perturbations operate on the resized 128×128 grayscale grid, not raw acquisition data.</p>
<h2>Limits and decision</h2><p>One training seed; no confidence intervals, external validation or verified patient independence. The experiment was motivated by development results, so gains on those stress conditions are not independent evidence. No segmentation or DWI model was retrained. No automatic model promotion.</p><p><a href="summary.json">Full verified metrics</a></p></html>'''
    (args.output/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({name:row['accuracy_delta_pp'] for name,row in comparison.items()},indent=2))


if __name__=='__main__':main()
