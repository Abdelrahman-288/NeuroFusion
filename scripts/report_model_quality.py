"""Apply the pre-recorded tumor/stroke development checks after both runs finish."""
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.model_quality import compare_tumor,compare_stroke

root=Path(__file__).resolve().parents[1];out=root/'experiments/model-quality-001'
if (out/'summary.json').exists():raise ValueError('Comparison already exists')
read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
protocol=read('experiments/model-quality-001/protocol.json')
for name,sha in protocol['baseline_sha256'].items():
    if digest(root/'experiments'/name/'last.pt')!=sha:raise ValueError('Baseline changed')
for path,sha in protocol['split_sha256'].items():
    if digest(root/path)!=sha:raise ValueError('Split changed')
for name in ('tumor-seg-continuation-001','dwi-continuation-002'):
    proof=read(f'experiments/{name}/checkpoint-reproduction.json')
    if not proof['passed'] or proof['checkpoint_sha256']!=digest(root/'experiments'/name/'last.pt'):raise ValueError('Checkpoint verification missing')
for name in ('tumor-seg-001','tumor-seg-continuation-001'):
    if not read(f'experiments/{name}/verification.json')['passed']:raise ValueError('Tumor metric audit missing')
tumor=compare_tumor(read('experiments/tumor-seg-001/validation.json'),read('experiments/tumor-seg-continuation-001/validation.json'))
stroke_cases=[]
for name in ('dwi-component-001','dwi-continuation-002'):
    report=read(f'experiments/{name}/summary.json');assert not report['holdout_evaluated']
    cases=report['final_validation']['cases']
    for case in cases:
        p=root/'experiments'/name/'predictions'/f'{case["subject"]}-probability.nii.gz'
        image=nib.load(p);scale={'mm':1.,'meter':1000.,'micron':.001}.get(image.header.get_xyzt_units()[0])
        if scale is None:raise ValueError('Unknown physical units')
        case['false_positive_ml']=case['false_positive_voxels']*abs(np.linalg.det(image.affine[:3,:3]))*scale**3/1000
    stroke_cases.append(cases)
stroke=compare_stroke(*stroke_cases,read('experiments/lesion-analysis-component-001/summary.json')['primary'],read('experiments/lesion-analysis-continuation-001/summary.json')['primary'])
result={'protocol_sha256':digest(out/'protocol.json'),'tumor':tumor,'stroke':stroke,'automatic_promotion':False,
    'independent_qualification_complete':False,'holdout_used':False,'ucsf_cohort_used':False,
    'note':'Fixed epoch-10 development comparison. No clinical qualification or multi-seed confirmation. Original failed experiments and UCSF gates remain unchanged.'}
save_json(out/'summary.json',result)
sections=[]
for task,result_task in [('Tumor segmentation',tumor),('Stroke segmentation',stroke)]:
    rows=''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td><td>{html.escape(str(result_task["candidate"][k]))}</td></tr>' for k,v in result_task['baseline'].items())
    checks=''.join('<li>'+html.escape(k.replace('_',' '))+': '+('PASS' if v else 'FAIL')+'</li>' for k,v in result_task['checks'].items())
    sections.append(f'<section><h2>{task}</h2><p>Development screen: {"PASS" if result_task["development_screen_passed"] else "FAIL"}</p><table><tr><th>Metric</th><th>Epoch 5</th><th>Epoch 10</th></tr>{rows}</table><ul>{checks}</ul><p>Paired development Dice change: {result_task["dice_delta"]["mean_delta"]:.4f}; exploratory interval {result_task["dice_delta"]["percentile_95_interval"]}.</p></section>')
(out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Model quality comparison</title><style>body{font:16px system-ui;max-width:1150px;margin:30px auto;padding:20px;background:#101e2c;color:#eee}a{color:#80ded0}td,th{padding:12px;border-bottom:1px solid #456;text-align:left;overflow-wrap:anywhere}table{width:100%}section{overflow:auto}</style><h1>Tumor and stroke: fixed-budget continuation</h1><p>Five additional training epochs; same development partitions and threshold. Final checkpoint rule fixed before training. No holdout or new UCSF-cohort inference. No active model replaced.</p>'+''.join(sections)+'<p>These are development checks, not independent qualification. Multi-seed confirmation, source-independent evaluation and expert review remain.</p><p><a href="protocol.json">Prospective protocol</a> · <a href="summary.json">Full comparison</a></p></html>',encoding='utf-8')
print(json.dumps({'tumor_passed':tumor['development_screen_passed'],'stroke_passed':stroke['development_screen_passed']},indent=2))
