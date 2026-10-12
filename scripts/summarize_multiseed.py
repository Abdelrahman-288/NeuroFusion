"""Verify all paired artifacts and summarize three training seeds."""
import json
import argparse
from pathlib import Path
import numpy as np
from neurofusion.cohort import digest
from neurofusion.robustness import CONDITIONS,summarize
from neurofusion.tumor import CLASSES
from neurofusion.multiseed import statistics,screen
from neurofusion.data import save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contrast-only',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; exp=root/'experiments';out=exp/('contrast-multiseed-001' if args.contrast_only else 'multiseed-001')
    if (out/'summary.json').exists():raise ValueError('Summary already exists')
    protocol=json.loads((out/'protocol.json').read_text()); results={};proof={};reference_coverage=None;reference_protocol=None
    for seed in protocol['seeds']:
        results[seed]={}
        configs={}
        for variant in ['baseline','augmented']:
            if seed==42:
                run=exp/('tumor-cnn-002' if variant=='baseline' else 'tumor-cnn-aug-001')
                evaluation=exp/('robustness-tumor-001' if variant=='baseline' else 'robustness-tumor-aug-001')
            else:
                run=exp/f'tumor-{variant}-seed{seed}-001';evaluation=exp/f'robustness-{variant}-seed{seed}-001'
                if seed==43 and variant=='baseline':evaluation=exp/'robustness-baseline-seed43-002'
            if args.contrast_only and variant=='augmented':
                run=exp/f'tumor-contrast-seed{seed}-001';evaluation=exp/f'robustness-contrast-seed{seed}-001'
            config=json.loads((run/'config.json').read_text());configs[variant]=config
            if digest(Path(config['split_path']))!=config['split_sha256']:raise ValueError('Frozen split changed')
            training=json.loads((run/'summary.json').read_text());coverage=json.loads((evaluation/'coverage.json').read_text())
            evconfig=json.loads((evaluation/'config.json').read_text())
            if config['seed']!=seed or training['epochs']!=5 or training['updates']!=555 or not training['completed'] or training['test_evaluated']:raise ValueError('Training protocol mismatch')
            if variant=='augmented' and config['augmentation']['seed']!=seed+1000:raise ValueError('Augmentation RNG mismatch')
            if args.contrast_only and variant=='augmented':
                if {k:v for k,v in config['augmentation'].items() if k!='seed'}!=protocol['policy']:raise ValueError('Contrast policy mismatch')
            if variant=='baseline' and config.get('augmentation'):raise ValueError('Unexpected baseline augmentation')
            if digest(run/'last.pt')!=training['last_checkpoint_sha256'] or evconfig['checkpoint_sha256']!=training['last_checkpoint_sha256']:raise ValueError('Checkpoint mismatch')
            if coverage['test_loaded'] or coverage['partition']!='validation':raise ValueError('Unexpected partition')
            train_coverage=json.loads((run/'coverage.json').read_text())
            split=json.loads(Path(config['split_path']).read_text())
            for partition,key in [('train','train_paths'),('validation','validation_paths')]:
                expected=sorted(r['path'] for r in split['assignments'] if r['partition']==partition)
                if sorted(train_coverage[key])!=expected:raise ValueError('Training coverage mismatch')
            if train_coverage['test_loaded']:raise ValueError('Unexpected training test usage')
            if reference_coverage is not None and coverage!=reference_coverage:raise ValueError('Coverage differs')
            reference_coverage=coverage
            check={k:evconfig[k] for k in ['seed','conditions','partition','images','groups','split_sha256','domain']}
            if reference_protocol is not None and check!=reference_protocol:raise ValueError('Stress protocol differs')
            reference_protocol=check
            report=json.loads((evaluation/'summary.json').read_text())
            clean=np.load(evaluation/'clean.npz')['probabilities'];groups=[r['group_id'] for r in coverage['images']]
            saved={r['path']:r['probabilities'] for r in json.loads((run/'validation-predictions.json').read_text())}
            original=np.asarray([saved[r['path']] for r in coverage['images']])
            if np.max(np.abs(clean-original))>1e-4 or not np.array_equal(clean.argmax(1),original.argmax(1)):raise ValueError('Clean reproduction failed')
            for condition in CONDITIONS:
                with np.load(evaluation/(condition+'.npz')) as data:
                    if not np.array_equal(data['labels'],[CLASSES.index(r['label']) for r in coverage['images']]):raise ValueError('Labels differ')
                    measured=summarize(data['labels'],data['probabilities'],clean,groups)
                if measured!=report['conditions'][condition]:raise ValueError('Metrics differ')
            results[seed][variant]=report['conditions']
            proof[f'{seed}-{variant}']={'checkpoint_sha256':training['last_checkpoint_sha256'],'evaluation_summary_sha256':digest(evaluation/'summary.json'),'clean_reproduction_max_difference':report['clean_baseline_max_difference']}
        for key in ['architecture','seed','epochs','batch_size','learning_rate','optimizer','split_sha256','classes']:
            if configs['baseline'][key]!=configs['augmented'][key]:raise ValueError('Paired training control differs')
    conditions={}
    for condition in CONDITIONS:
        base=[results[s]['baseline'][condition]['accuracy'] for s in protocol['seeds']]
        aug=[results[s]['augmented'][condition]['accuracy'] for s in protocol['seeds']]
        conditions[condition]={'baseline_accuracy':statistics(base),'augmented_accuracy':statistics(aug),'paired_delta_pp':statistics((np.asarray(aug)-base)*100)}
    clean_delta=[100*(results[s]['augmented']['clean']['accuracy']-results[s]['baseline']['clean']['accuracy']) for s in protocol['seeds']]
    f1_delta=[results[s]['augmented']['clean']['macro_f1']-results[s]['baseline']['clean']['macro_f1'] for s in protocol['seeds']]
    recalls={c:[100*(results[s]['augmented']['clean']['per_class'][i]['recall']-results[s]['baseline']['clean']['per_class'][i]['recall']) for s in protocol['seeds']] for i,c in enumerate(CLASSES)}
    stress=[float(np.mean([100*(results[s]['augmented'][c]['accuracy']-results[s]['baseline'][c]['accuracy']) for c in CONDITIONS[1:]])) for s in protocol['seeds']]
    decision=screen(clean_delta,f1_delta,recalls,stress,protocol['development_candidate_gates'])
    summary={'policy':protocol.get('policy','combined-intensity'),'seeds':protocol['seeds'],'conditions':conditions,'per_seed':results,'clean_recall_delta_pp':{k:statistics(v) for k,v in recalls.items()},'stress_mean_delta_pp':statistics(stress),'decision':decision,'verified':True,'test_loaded':False,'viewer_model_changed':False,'provenance':proof}
    save_json(out/'summary.json',summary)
    table=''.join(f'<tr><td>{c}</td><td>{v["baseline_accuracy"]["mean"]:.2%} ± {v["baseline_accuracy"]["sample_std"]:.2%}</td><td>{v["augmented_accuracy"]["mean"]:.2%} ± {v["augmented_accuracy"]["sample_std"]:.2%}</td><td>{v["paired_delta_pp"]["mean"]:+.2f} ± {v["paired_delta_pp"]["sample_std"]:.2f}</td></tr>' for c,v in conditions.items())
    checks=''.join(f'<li>{k}: {"PASS" if v else "FAIL"}</li>' for k,v in decision['checks'].items())
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NeuroFusion multi-seed comparison</title><style>body{{font:17px system-ui;max-width:1100px;margin:40px auto;padding:24px;color:#18364b}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}.notice{{background:#fff1ce;padding:20px}}</style><h1>Three-seed augmentation comparison</h1><p>Seeds 42, 43, 44 · six trained models · 943 validation images per condition · test unused</p><p class="notice">Mean ± sample standard deviation across training seeds, not confidence intervals. The same validation images are reused. No automatic model promotion.</p><div style="overflow-x:auto"><table><tr><th>Condition</th><th>Baseline accuracy</th><th>Augmented accuracy</th><th>Paired change (pp)</th></tr>{table}</table></div><h2>Development screening</h2><ul>{checks}</ul><p>Criteria were fixed before seeds 43 and 44; seed 42 had already been observed. Passing supports further independent evaluation only. Current viewer checkpoint remains unchanged.</p><h2>Limits</h2><p>Three seeds do not establish population uncertainty. No external validation, verified patient independence, calibrated uncertainty or clinical readiness. Synthetic stress conditions were already used during development. These findings cover only the tumor classifier.</p><p><a href="summary.json">All metrics and provenance</a> · <a href="protocol.json">Screening protocol</a></p></html>'''
    if args.contrast_only:
        page=page.replace('Three-seed augmentation comparison','Three-seed contrast-only comparison').replace('Criteria were fixed before seeds 43 and 44; seed 42 had already been observed.','The same screening criteria were retained before these three runs. Prior development results informed this policy: apply contrast 0.8–1.0 around 0.5 to 30% of training images; no brightness or noise augmentation. Baseline runs are reused.')
    (out/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({'conditions':conditions,'recalls':summary['clean_recall_delta_pp'],'decision':decision},indent=2))


if __name__=='__main__':main()
