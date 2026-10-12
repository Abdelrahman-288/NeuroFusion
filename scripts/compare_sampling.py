"""Compare fixed final-epoch validation results for two sampling strategies."""
import argparse
import html
import json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['sampling','fusion'],default='sampling')
    for name in ['baseline','candidate','baseline-analysis','candidate-analysis','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    configs=[read(p/'config.json') for p in [args.baseline,args.candidate]]
    changed=[k for k in set(configs[0])|set(configs[1]) if configs[0].get(k)!=configs[1].get(k)]
    allowed={'sampling'} if args.kind=='sampling' else {'architecture','inputs','preprocessing'}
    if set(changed)!=allowed:
        raise ValueError(f'Unexpected configuration differences: {changed}')
    if args.kind=='fusion' and (configs[0].get('inputs',['dwi'])!=['dwi'] or configs[1].get('inputs')!=['dwi','adc']):
        raise ValueError('Fusion comparison requires DWI baseline and DWI/ADC candidate')
    summaries=[read(p/'summary.json') for p in [args.baseline,args.candidate]]
    reports=[read(p/'summary.json') for p in [args.baseline_analysis,args.candidate_analysis]]
    protocols=[read(p/'protocol.json') for p in [args.baseline_analysis,args.candidate_analysis]]
    for key in ['total_epochs','steps','train_studies','validation_studies']:
        if summaries[0][key]!=summaries[1][key]:
            raise ValueError(f'Run budget differs: {key}')
    for key in ['probability_threshold','connectivity','minimum_component_size_voxels','primary_matching','sensitivity_checks','size_bins_ml','scipy','manifest_sha256','splits_sha256']:
        if protocols[0][key]!=protocols[1][key]:
            raise ValueError(f'Evaluation protocol differs: {key}')
    for run,summary,report,protocol in zip([args.baseline,args.candidate],summaries,reports,protocols):
        if digest(run/'last.pt')!=protocol['last_checkpoint_sha256'] or summary['holdout_evaluated'] or report['holdout_evaluated']:
            raise ValueError('Checkpoint or holdout verification failed')
    cases=[{c['subject']:c for c in r['cases']} for r in reports]
    if set(cases[0])!=set(cases[1]):
        raise ValueError('Validation subjects differ')
    rows=[]
    def add(name,a,b):
        rows.append({'metric':name,'baseline':a,'candidate':b,'change':b-a})
    add('Mean voxel Dice',*[s['final_validation']['mean_dice'] for s in summaries])
    add('Mean absolute volume error (mL)',*[s['final_validation']['mean_absolute_volume_error_ml'] for s in summaries])
    for key in ['matched_pairs','lesion_recall','lesion_precision','lesion_f1','unmatched_components_per_scan','no_overlap_predicted_components']:
        add(key,*[r['primary'][key] for r in reports])
    for size in reports[0]['by_reference_size']:
        a,b=[r['by_reference_size'][size] for r in reports]
        if a['reference_lesions']!=b['reference_lesions']:
            raise ValueError('Reference size counts changed')
        add(f'Recall: {size}',a['recall'],b['recall'])
    paired=[{'subject':s,'baseline_dice':cases[0][s]['dice'],'candidate_dice':cases[1][s]['dice'],
             'dice_change':cases[1][s]['dice']-cases[0][s]['dice']} for s in sorted(cases[0])]
    result={'kind':args.kind,'configuration_differences':sorted(changed),'epochs':summaries[0]['total_epochs'],
            'steps_each':summaries[0]['steps'],'validation_studies':len(paired),
            'holdout_evaluated':False,'metrics':rows,'paired_cases':paired,
            'limitations':'One seed, five epochs, development validation. No statistical or clinical superiority claim.'}
    args.output.mkdir(parents=True)
    save_json(args.output/'comparison.json',result)
    table=''.join(f'<tr><td>{html.escape(r["metric"])}</td><td>{r["baseline"]:.4f}</td><td>{r["candidate"]:.4f}</td><td>{r["change"]:+.4f}</td></tr>' for r in rows)
    case_table=''.join(f'<tr><td>{c["subject"]}</td><td>{c["baseline_dice"]:.4f}</td><td>{c["candidate_dice"]:.4f}</td><td>{c["dice_change"]:+.4f}</td></tr>' for c in sorted(paired,key=lambda c:c['dice_change']))
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>NeuroFusion sampling comparison</title><style>body{font:17px system-ui;max-width:1100px;margin:35px auto;padding:20px;color:#173348}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}</style><h1>Voxel versus component-balanced sampling</h1><p>Same architecture, seed, study order and 6,960-update budget. Final epoch compared on 37 validation studies. Sampling changes RNG consumption. No holdout evaluation.</p><p>Recall and precision below are fractions. Higher overlap scores are better; lower volume error and unmatched predictions are better. One-to-one component matching uses threshold 0.5 and any positive overlap.</p><table><tr><th>Metric</th><th>Voxel baseline</th><th>Component sampler</th><th>Change</th></tr>'+table+'</table><h2>Per-study Dice changes</h2><table><tr><th>Subject</th><th>Baseline</th><th>Candidate</th><th>Change</th></tr>'+case_table+'</table><p>Exploratory single-seed comparison; validation guided this experiment. No clinical or statistical superiority claim.</p>',encoding='utf-8')
    if args.kind=='fusion':
        page=(args.output/'index.html').read_text(encoding='utf-8')
        page=page.replace('NeuroFusion sampling comparison','NeuroFusion input fusion comparison').replace('Voxel versus component-balanced sampling','DWI versus DWI + ADC input fusion').replace('Voxel baseline','DWI only').replace('Component sampler','DWI + ADC').replace('Same architecture, seed, study order and 6,960-update budget. Final epoch compared on 37 validation studies. Sampling changes RNG consumption.','Same component sampler, seed, study order and training budget. Final epoch compared on the same validation studies. Adding the ADC channel changes the first layer and initialization; this is an exploratory input-fusion comparison.')
        (args.output/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({'metrics':rows,'validation_studies':len(paired)},indent=2))


if __name__=='__main__':
    main()
