"""Publish all paired-seed outcomes without averaging away a failed check."""
import html
import json
from pathlib import Path
from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.model_quality import compare_tumor

root=Path(__file__).resolve().parents[1];out=root/'experiments/tumor-continuation-confirmation-001'
if (out/'summary.json').exists():raise ValueError('Confirmation snapshot already exists')
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
records=[]
for seed,baseline,candidate in [(42,'tumor-seg-001','tumor-seg-continuation-001'),
    (43,'tumor-seg-seed43-005-recovery','tumor-seg-seed43-010'),
    (44,'tumor-seg-seed44-005','tumor-seg-seed44-010')]:
    a=root/'experiments'/baseline;b=root/'experiments'/candidate
    ca=read(a/'config.json');cb=read(b/'config.json')
    if ca['seed']!=seed or cb['seed']!=seed or ca['epochs']!=5 or cb['epochs']!=10:
        raise ValueError('Unexpected seed or training budget')
    if {k:v for k,v in ca.items() if k!='epochs'}!={k:v for k,v in cb.items() if k!='epochs'}:
        raise ValueError('Paired configuration differs')
    request=read(b/'run-request.json')
    if request['resume_sha256']!=digest(a/'last.pt'):raise ValueError('Continuation used a different baseline')
    for run in (a,b):
        verification=read(run/'verification.json')
        if not verification['passed'] or verification['last_sha256']!=digest(run/'last.pt'):
            raise ValueError('Metric verification missing or checkpoint changed')
    reproduced=read(b/'checkpoint-reproduction.json')
    if not reproduced['passed'] or reproduced['case_count']!=721 or reproduced['checkpoint_sha256']!=digest(b/'last.pt'):
        raise ValueError('Candidate reproduction missing')
    result=compare_tumor(read(a/'validation.json'),read(b/'validation.json'))
    records.append({'seed':seed,'baseline_run':baseline,'candidate_run':candidate,
        'baseline_checkpoint_sha256':digest(a/'last.pt'),'candidate_checkpoint_sha256':digest(b/'last.pt'),**result})
summary={'protocol_sha256':digest(out/'protocol.json'),'records':records,
    'all_seeds_passed':all(r['development_screen_passed'] for r in records),
    'seeds_passed':sum(r['development_screen_passed'] for r in records),'seeds_total':3,
    'independently_qualified':False,'production_model_changed':False,'holdout_evaluated':False,
    'note':'Three paired five-to-ten-epoch development comparisons. Image-group rather than verified-patient partitions. Positive-only segmentation. No independent validation or negative-case specificity estimate.'}
save_json(out/'summary.json',summary)
destination=root/'experiments/model-quality-001'
save_json(destination/'tumor-confirmation.json',summary)
page=destination/'index.html'
table=''.join(f'<tr><td>{r["seed"]}</td><td>{r["baseline"]["mean_dice"]:.4f}</td><td>{r["candidate"]["mean_dice"]:.4f}</td><td>{sum(r["checks"].values())}/5</td><td>'+html.escape(', '.join(k for k,v in r['checks'].items() if not v) or 'None')+'</td></tr>' for r in records)
section=f'<section><h2>Tumor paired-seed confirmation</h2><p>{summary["seeds_passed"]}/3 seeds passed all five pre-recorded development checks. No model promotion.</p><table><tr><th>Seed</th><th>Epoch-5 Dice</th><th>Epoch-10 Dice</th><th>Checks</th><th>Failed checks</th></tr>{table}</table><p><a href="tumor-confirmation.json">Full confirmation evidence</a></p></section>'
content=page.read_text(encoding='utf-8').replace(
    'Multi-seed confirmation, source-independent evaluation and expert review remain.',
    'The paired-seed results are below. Source-independent evaluation and expert review remain.')
page.write_text(content.replace('</html>',section+'</html>'),encoding='utf-8')
print(json.dumps({'seeds_passed':summary['seeds_passed'],'total':3}))
