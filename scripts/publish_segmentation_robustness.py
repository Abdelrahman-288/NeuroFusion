"""Publish the verified development robustness experiment without waiving failures."""
import argparse,html,json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    report=json.loads((a.run/'summary.json').read_text());verification=json.loads((a.run/'verification.json').read_text())
    if not verification['passed'] or not report['testing_complete']:raise ValueError('Verification required')
    lines=['# Tumor segmentation and stroke robustness','',
        '11 October 2026. Completed the requested testing extension on the active checkpoints. '
        'Testing completion does not mean every perturbation passed or that the models are clinically robust.','',
        'All 721 tumor-positive BRISC validation images and 37 ISLES validation volumes were evaluated under six conditions each. '
        'The threshold stayed at 0.5. No training, model promotion, downloads or protected holdout use occurred.','']
    tables=[]
    for task,unit in [('tumor','pixels'),('stroke','mL')]:
        lines += [f'## {task.capitalize()} results','',
            f'False positives and absolute size error are measured in {unit}; metrics are averaged per image or volume.', '',
            '| Condition | Mean Dice | Dice change | False positives | Absolute size error | New zero-overlap cases |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
        rows=[]
        for condition,r in report[task].items():
            cells=[condition,f'{r["dice"]:.4f}',f'{r["dice_change"]:+.4f}',f'{r["false_positive"]:.3f}',f'{r["volume_error"]:.3f}',str(len(r['new_zero_overlap']))]
            lines.append('| '+' | '.join(cells)+' |')
            rows.append('<tr>'+''.join('<td>'+html.escape(c)+'</td>' for c in cells)+'</tr>')
        lines += ['', 'Conditions flagged by the predeclared descriptive rule (mean Dice loss greater than 0.05 or any new zero-overlap case): '+
            ', '.join(c for c,r in report[task].items() if any(r['development_flags'].values()))+'.','']
        tables.append(f'<h2>{task.capitalize()}</h2><p>False positives and size error: {unit}</p><div class="scroll"><table><tr><th>Condition</th><th>Dice</th><th>Change</th><th>False positives</th><th>Size error</th><th>New zero-overlap</th></tr>'+''.join(rows)+'</table></div>')
    lines += ['## Protocol and verification','',
        'Tumor perturbations reuse the classifier suite: brightness ×0.8/1.2, contrast ×0.8 around 0.5, Gaussian noise SD0.03, and Gaussian blur sigma1 pixel, after 128×128 preprocessing. Results are scored at original image dimensions.','',
        'DWI perturbations operate after z-score normalization: scale ×0.8/1.2, offset +0.2, Gaussian noise SD0.1, and isotropic Gaussian blur sigma1 voxel. Offset and noise affect background too. No clipping or renormalization is applied. These are controlled model-input stresses, not simulations of MRI acquisition artifacts.','',
        f'{verification["prediction_files_verified"]} prediction archives were hash-verified and all {verification["paired_metrics_replayed"]} paired case-condition metrics replayed exactly. Clean tumor and stroke predictions reproduced historical saved predictions within numerical tolerance with unchanged binary masks.','',
        'Fixed flags are descriptive, not clinically validated acceptance limits. Individual new misses remain visible even when average Dice improves. No failure is used to select a different threshold.','',
        '## Remaining limits','']+['- '+x for x in report['limitations']]+['',
        'The requested robustness testing extension is implemented. Failures require separate model-quality work; independent scanner/site robustness is not established.','',
        'Evidence: `experiments/segmentation-robustness-001/` contains the frozen protocol, source hashes, coverage, per-case metrics, full predictions, summaries and verification.','',
        'Reproduce with `scripts/evaluate_segmentation_robustness.py --output <fresh-directory>`, then `scripts/verify_segmentation_robustness.py --run <directory>`.']
    (root/'docs/SEGMENTATION_ROBUSTNESS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Segmentation robustness</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:24px;background:#0b1726;color:#e5eef8}td,th{padding:12px;text-align:left;border-bottom:1px solid #456}.scroll{overflow:auto}.notice{padding:16px;background:#3b3020}a{color:#80ded0}</style><h1>Tumor and stroke robustness</h1><p>721 tumor validation images · 37 stroke validation volumes · six conditions per task</p><p class="notice">Testing completed and metric replay verified. Development stress tests are not independent or clinical qualification. New zero-overlap cases indicate previously overlapping predictions that miss the reference entirely after perturbation.</p>'+''.join(tables)+'<h2>Limits</h2><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in report['limitations'])+'</ul><p><a href="summary.json">Summary</a> · <a href="protocol.json">Protocol</a> · <a href="verification.json">Verification</a></p></html>'
    (a.run/'index.html').write_text(page,encoding='utf-8')
    print('Published docs/SEGMENTATION_ROBUSTNESS.md and experiment index.html')


if __name__=='__main__':main()
