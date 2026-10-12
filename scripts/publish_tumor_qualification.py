"""Publish the completed checks without turning development evidence into qualification."""
import html
import json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1]
run=root/'experiments/tumor-qualification-001'
summary=json.loads((run/'summary.json').read_text())
verification=json.loads((run/'verification.json').read_text())
if not verification['passed'] or verification['summary_sha256']!=digest(run/'summary.json'):
    raise ValueError('Verified summary required')
seeds=summary['segmentation'];classifier=summary['classifier']
checks=[dict(id='application_compatibility',status='passed' if all(r['compatibility_passed'] for r in seeds) else 'failed'),
        dict(id='segmentation_development_quality',status='passed' if all(r['development_quality_passed'] for r in seeds) else 'failed'),
        dict(id='segmentation_development_uncertainty',status='passed' if all(r['uncertainty_passed'] for r in seeds) else 'failed'),
        dict(id='classifier_development_uncertainty',status='passed' if classifier['uncertainty_passed'] else 'failed'),
        dict(id='numerical_recomputation',status='passed'),
        dict(id='patient_independent_qualification',status='blocked'),
        dict(id='segmentation_screening_specificity',status='not_established')]
decision=dict(checks_completed=True,checks=checks,qualified=False,promotion_permitted=False,
              clinical_ready=False,blockers=summary['blockers'],summary_sha256=digest(run/'summary.json'))
save_json(run/'qualification-decision.json',decision)
lines=['# Tumor model compatibility, uncertainty and qualification checks','',
       'Completed 10 October 2026 using local BRISC development data only. No downloads, protected-test inference, model replacement or expert review.', '',
       '## Decision','',
       '**Checks completed; independent qualification remains blocked.** Completing an evaluation does not make a failing or unresolved requirement pass.','',
       '| Check | Result |','| --- | --- |']
lines += [f'| {r["id"]} | {r["status"]} |' for r in checks]
lines += ['', '## Improved segmentation checkpoints','',
          'All three epoch-10 checkpoints were loaded through the application loader and evaluated on the same 721 positive images. Each was exercised through the actual viewer analysis path. Calibration uses 358 fit images and 363 evaluation images in disjoint image-similarity groups. These are reused development data, not independent patients.','',
          '| Seed | Compatibility | Temperature | NLL before → after | Brier before → after | Retained coverage | Dice among retained / all evaluation images |',
          '| --- | --- | --- | --- | --- | --- | --- |']
for r in seeds:
    s=r['selective']
    retained=f'{1-s["accepted_risk"]:.4f}' if s['accepted_risk'] is not None else 'none'
    lines.append(f'| {r["seed"]} | {r["compatibility_passed"]} | {r["temperature"]} | {r["before"]["nll"]:.5f} → {r["after"]["nll"]:.5f} | {r["before"]["brier"]:.5f} → {r["after"]["brier"]:.5f} | {s["coverage"]:.1%} | {retained} / {1-s["overall_risk"]:.4f} |')
lines += ['', 'Binary calibration metrics use 4,096 fixed native-grid pixel samples per image, including background. Their low values must not be interpreted as lesion detection accuracy; foreground/background imbalance matters. Temperature scaling preserves the 0.5 decision boundary. Abstention is a development simulation, not enabled in the live application.','',
          '## Existing classifier','',
          'There is no newly trained improved classifier checkpoint in this experiment. The existing classifier was checked separately; segmentation calibration does not validate classification scores.', '',
          f'Temperature: {classifier["temperature"]:.4f}. Evaluation NLL: {classifier["before"]["nll"]:.4f} → {classifier["after"]["nll"]:.4f}. ECE: {classifier["before"]["ece_10_equal_width"]:.4f} → {classifier["after"]["ece_10_equal_width"]:.4f}. All uncertainty checks passed: {classifier["uncertainty_passed"]}.','',
          '## Qualification limitations','']
lines += ['- '+x for x in summary['blockers']]
lines += ['', 'The protected test partition was not opened to resolve these limitations. Mandatory expert review remains removed. No passing independent result or patient identity was invented. The promotion registry is unchanged.','',
          '## Evidence','',
          '- `experiments/tumor-qualification-001/protocol.json`: criteria saved before scoring.',
          '- `summary.json` and per-seed JSON: measured results, including failed checks.',
          '- `verification.json`: independently recomputed NLL/Brier, classifier metrics, selective risk and group separation.',
          '- `qualification-decision.json`: explicit pass/fail/blocked disposition.',
          '- Saved NPZ files permit numerical replay; viewer outputs demonstrate candidate integration without promotion.','']
document='\n'.join(lines)
(root/'docs/TUMOR_QUALIFICATION.md').write_text(document,encoding='utf-8')
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tumor qualification</title><style>body{font:16px system-ui;background:#101b2b;color:#e5eef8;max-width:1100px;margin:32px auto;padding:20px}pre{white-space:pre-wrap;line-height:1.7}a{color:#80ded0}</style><h1>Tumor qualification checks</h1><p>Checks complete. Independent qualification remains blocked. No model promoted.</p><pre>'+html.escape(document)+'</pre><a href="summary.json">Measured results</a> · <a href="qualification-decision.json">Qualification decision</a></html>'
(run/'index.html').write_text(page,encoding='utf-8')
progress_path=root/'docs/progress_tracker.json';progress=json.loads(progress_path.read_text())
progress['tumor_qualification']=dict(checks_completed=True,qualified=False,checks=checks,
                                    evidence='docs/TUMOR_QUALIFICATION.md',data_downloaded=False,model_promoted=False)
save_json(progress_path,progress)
print(json.dumps(decision,indent=2))
