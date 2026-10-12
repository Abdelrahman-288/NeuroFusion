"""Evaluate the pinned tumor classifier on all frozen development validation images."""
import argparse
import html
import json
from pathlib import Path
import shutil
import numpy as np
import torch
from neurofusion.cohort import digest
from neurofusion.inference import Predictor, MODELS
from neurofusion.tumor import load_partition, CLASSES
from neurofusion.tumor import TumorCNN
from neurofusion.robustness import CONDITIONS, perturb, summarize
from neurofusion.data import save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run',type=Path,help='Local trained run to evaluate; defaults to the pinned baseline')
    args=parser.parse_args()
    if args.output.exists(): parser.error('Choose a fresh output directory')
    project=Path(__file__).resolve().parents[1]
    baseline=args.run or project/'experiments/tumor-cnn-002'
    config=json.loads((baseline/'config.json').read_text())
    split=Path(config['split_path'])
    if digest(split)!=config['split_sha256']: raise ValueError('Frozen split changed')
    images,labels,rows=load_partition(config['root'],split,'validation')
    groups=[r['group_id'] for r in rows]
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if args.run:
        expected=json.loads((baseline/'summary.json').read_text())['last_checkpoint_sha256']
        if digest(baseline/'last.pt')!=expected: raise ValueError('Checkpoint changed')
        torch.set_num_threads(2)
        model=TumorCNN().to(device)
        model.load_state_dict(torch.load(baseline/'last.pt',map_location='cpu',weights_only=True)['model'])
        model.eval()
    else:
        expected=MODELS['tumor_classifier'][1]
        predictor=Predictor(project,device); model=predictor.model('tumor_classifier')
    torch.use_deterministic_algorithms(True)
    seed=20261006
    args.output.mkdir(parents=True)
    save_json(args.output/'config.json',{'seed':seed,'conditions':list(CONDITIONS),'partition':'validation',
        'images':len(rows),'groups':len(set(groups)),'test_loaded':False,'split_sha256':digest(split),
        'checkpoint_sha256':expected,'run':str(baseline.resolve()),'device':device,'torch':str(torch.__version__),
        'numpy':np.__version__,'domain':'post-resize 128x128 grayscale [0,1]; no clinical acquisition simulation'})
    source=args.output/'source';source.mkdir()
    for path in [Path(__file__),project/'src/neurofusion/robustness.py',project/'src/neurofusion/tumor.py']:
        shutil.copy2(path,source/path.name)
    save_json(args.output/'source-hashes.json',{p.name:digest(p) for p in source.iterdir()})
    save_json(args.output/'coverage.json',{'partition':'validation','test_loaded':False,
        'images':[{'path':r['path'],'sha256':r['sha256'],'group_id':r['group_id'],'label':r['label']} for r in rows]})
    old={r['path']:r['probabilities'] for r in json.loads((baseline/'validation-predictions.json').read_text())}
    if set(old)!={r['path'] for r in rows}: raise ValueError('Baseline coverage mismatch')
    summaries={}; clean=None
    for condition in CONDITIONS:
        values=perturb(images.astype(np.float32)/255,condition,seed)
        probabilities=[]
        with torch.inference_mode():
            for start in range(0,len(values),32):
                probabilities.append(model(torch.from_numpy(values[start:start+32]).to(device)).softmax(1).cpu().numpy())
        probabilities=np.concatenate(probabilities)
        if condition=='clean':
            clean=probabilities
            difference=float(np.max(np.abs(clean-np.asarray([old[r['path']] for r in rows]))))
            previous=np.asarray([old[r['path']] for r in rows])
            # CPU normalization in this stress harness versus CUDA normalization
            # during training can cause small float32 differences. Require both
            # a bounded score difference and identical predicted classes.
            if difference>1e-4 or not np.array_equal(clean.argmax(1),previous.argmax(1)):
                raise ValueError(f'Clean baseline failed reproduction: {difference}')
        summaries[condition]=summarize(labels,probabilities,clean,groups)
        np.savez_compressed(args.output/(condition+'.npz'),probabilities=probabilities,labels=labels)
        print(condition,json.dumps({k:summaries[condition][k] for k in ['accuracy','macro_f1','flip_rate','correct_to_wrong','wrong_to_correct']}),flush=True)
    report={'conditions':summaries,'clean_baseline_max_difference':difference,'clean_reproduction_tolerance':1e-4,'clean_labels_identical':True,'test_loaded':False,
            'limitations':['Development validation only; no external validation.',
            'Similarity groups are not verified patients. No confidence intervals or clinical robustness claims.',
            'Synthetic perturbations after resizing do not represent scanner or hospital variation.',
            'Only the tumor classifier was evaluated; segmentation and DWI robustness remain pending.',
            'No model selection, retraining or calibrated abstention performed.']}
    save_json(args.output/'summary.json',report)
    table=''.join('<tr><td>'+html.escape(name)+'</td>'+''.join(f'<td>{scores[k]:.2%}</td>' for k in ['accuracy','macro_f1','flip_rate','equal_group_accuracy'])+f'<td>{scores["correct_to_wrong"]}</td><td>{scores["wrong_to_correct"]}</td></tr>' for name,scores in summaries.items())
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NeuroFusion robustness evaluation</title>
<style>body{{font:17px system-ui;max-width:1150px;margin:40px auto;padding:24px;color:#18364b}}h1{{color:#11665e}}td,th{{padding:12px;border-bottom:1px solid #cbd5df;text-align:left}}.notice{{background:#fff1ce;padding:20px}}.table{{overflow-x:auto}}</style>
<h1>Tumor classifier robustness evaluation</h1><p>{len(rows)} frozen validation images / {len(set(groups))} similarity groups / six conditions / held-out test unused</p>
<p class="notice">Research stress test, not clinical validation. The clean model was reproduced before comparing perturbations. No_tumor does not mean healthy.</p>
<div class="table"><table><tr><th>Condition</th><th>Accuracy</th><th>Macro F1</th><th>Label flips</th><th>Group accuracy</th><th>Correct → wrong</th><th>Wrong → correct</th></tr>{table}</table></div>
<h2>Fixed protocol</h2><p>Applied after grayscale resizing to 128 × 128, intensities [0,1]. Brightness multiplies by 0.8 or 1.2. Contrast scales by 0.8 around 0.5. Noise is independent Gaussian with standard deviation 0.03, seed {seed}. Blur is Gaussian with sigma 1 pixel, reflected boundaries. All outputs clipped to [0,1]. No geometric or label transformations.</p>
<p>Label flips compare each condition with clean predictions, not with reference labels. Group accuracy weights each similarity group equally. Macro F1 is the unweighted mean over four classes.</p>
<h2>Scope and limits</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in report['limitations'])}</ul><p><a href="summary.json">Full metrics</a> · <a href="coverage.json">Coverage</a> · <a href="config.json">Configuration</a></p></html>'''
    (args.output/'index.html').write_text(page,encoding='utf-8')


if __name__=='__main__': main()
