"""Publish verified refinement results without overwriting earlier qualification."""
import html
import json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.ucsf_confirmation import confirm_pairs

root=Path(__file__).resolve().parents[1];run=root/'experiments/ucsf-refinement-001'
read=lambda p:json.loads(p.read_text())
summary=read(run/'summary.json');verification=read(run/'verification.json')
if not verification['passed'] or digest(run/'summary.json')!=verification['summary_sha256']:raise ValueError('Verified results required')
old_protocol=read(root/'configs/ucsf_clipping_confirmation_protocol.json')
pairs={seed:(read(root/old_protocol['controls'][str(seed)]/'summary.json'),read(run/f'seed{seed}'/'summary.json')) for seed in (42,43,44)}
historical_comparison=confirm_pairs(pairs)
save_json(run/'original-control-comparison.json',historical_comparison)
lines=['# UCSF specialist refinement — 10 October 2026','',
       '**Fixed three-seed training and evaluation completed. No active model changed.**','',
       'Each stabilized, clipped epoch-5 model received five additional epochs at learning rate 0.0003 with a reset Adam optimizer. The architecture, loss, threshold 0.5, uniform training-slice sampling, clipping norm 1 and AMP remain unchanged. Only the final epoch was eligible; no best-epoch selection was used.','',
       'The same 16 training and four development-validation patients were used. The separately acquired protected 20-patient cohort was not used. No data was downloaded.','',
       '## New comparison against stabilized controls','',
       'This is an explicitly new experiment, not a reinterpretation of the original failed clipping comparison. All four prior relative checks plus no newly zero-Dice patient must pass in every seed.','',
       '| Seed | Control Dice | Refined Dice | Control FP mL | Refined FP mL | Checks |','| --- | --- | --- | --- | --- | --- |']
for seed,result in summary['seeds'].items():
    m=result['means'];lines.append(f'| {seed} | {m["baseline_dice"]:.5f} | {m["candidate_dice"]:.5f} | {m["baseline_fp_ml"]:.3f} | {m["candidate_fp_ml"]:.3f} | {sum(result["gates"].values())}/5 |')
lines+=['',f'**Decision: {summary["decision"]}.**','']
for seed,result in summary['seeds'].items():
    failures=[name for name,passed in result['gates'].items() if not passed]
    lines.append(f'- Seed {seed}: '+(', '.join(failures)+' failed.' if failures else 'all new development checks passed.'))
lines+=['','## Original qualification remains separate','',
        f'Comparing these new candidates against the original unclipped controls: all seeds pass the original four checks = **{historical_comparison["all_seeds_passed"]}**. Full details are retained in `original-control-comparison.json`. The original seed-43 control predicts no foreground and has zero false positives. Improving its overlap does not automatically satisfy its zero-FP comparison. That failed rule is not silently relaxed.','',
        'Four repeatedly inspected patients cannot establish generalization. Passing a new development comparison would not itself satisfy target-contract, independence, uncertainty or independent-performance requirements. No result is labeled clinical qualification.','',
        '## Verification','',
        '- All 15 checkpoint epochs, protocol bindings and actual optimizer learning rates checked.',
        '- All 12 final patient masks and metric dictionaries reproduced after reloading checkpoints.',
        '- All 2,480 training slices covered in every refinement epoch.',
        '- Source and cache checksums and frozen patient roles checked.',
        '- Original and new comparison decisions retained; no promotion performed.','',
        'Evidence: `experiments/ucsf-refinement-001/` includes protocol, per-seed histories/checkpoints/predictions, final comparisons, original-control comparison and verification.','']
document='\n'.join(lines)
(root/'docs/UCSF_REFINEMENT.md').write_text(document,encoding='utf-8')
(run/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>UCSF refinement</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px}pre{white-space:pre-wrap;line-height:1.6}</style><h1>UCSF refinement results</h1><pre>'+html.escape(document)+'</pre>',encoding='utf-8')
progress_path=root/'docs/progress_tracker.json';progress=read(progress_path)
progress['ucsf_refinement']=dict(training_complete=True,seeds=3,new_comparison_passed=summary['all_seeds_passed'],
    original_comparison_passed=historical_comparison['all_seeds_passed'],independent_qualification=False,
    checkpoints_verified=15,masks_reproduced=12,model_promoted=False,evidence='docs/UCSF_REFINEMENT.md')
save_json(progress_path,progress)
print(document)
