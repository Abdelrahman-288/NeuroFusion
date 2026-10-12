"""Independently recompute saved predictions and show original-size tumor overlays."""
import argparse
from collections import Counter,defaultdict
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.tumor_segmentation import load_segmentation,native_probability,mask_metrics


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--run',type=Path,required=True)
    args=p.parse_args(); run=args.run; output=run/'report'
    if output.exists(): p.error('Report exists')
    config=json.loads((run/'config.json').read_text()); summary=json.loads((run/'summary.json').read_text())
    coverage=json.loads((run/'data-coverage.json').read_text()); cases=json.loads((run/'validation.json').read_text())
    if digest(Path(config['splits']))!=config['split_sha256'] or digest(run/'last.pt')!=summary['last_sha256']:
        raise ValueError('Split/checkpoint identity changed')
    if digest(Path(config['root'])/'manifest.json')!=config['publisher_manifest_sha256']:
        raise ValueError('Publisher manifest changed')
    _,_,native,rows=load_segmentation(config['root'],config['splits'],'validation')
    splits=json.loads(Path(config['splits']).read_text())
    expected_train=[r['path'] for r in splits['assignments'] if r['partition']=='train' and r['label']!='no_tumor']
    if Counter(r['path'] for r in coverage['train'])!=Counter(expected_train): raise ValueError('Training set mismatch')
    if Counter(r['path'] for r in cases)!=Counter(r['path'] for r in rows): raise ValueError('Validation coverage mismatch')
    if set(r['group_id'] for r in coverage['train'])&set(r['group_id'] for r in rows): raise ValueError('Group overlap')
    if config['test_loaded'] or coverage['test_loaded'] or summary['test_loaded']: raise ValueError('Test usage')
    history=json.loads((run/'history.json').read_text())
    if len(history)!=config['epochs'] or any(h['train_seen']!=len(expected_train) or h['validation_seen']!=len(rows) for h in history):
        raise ValueError('Epoch coverage mismatch')
    by_path={r['path']:(r,mask) for r,mask in zip(rows,native)}
    grouped=defaultdict(list)
    for case in cases:
        row,mask=by_path[case['path']]
        if row['group_id']!=case['group_id'] or row['label']!=case['label']: raise ValueError('Case label/group mismatch')
        path=run/'predictions'/case['prediction']
        if digest(path)!=case['prediction_sha256']: raise ValueError('Prediction changed')
        with np.load(path,allow_pickle=False) as saved: probability=native_probability(saved['probability'],mask.shape)
        result=mask_metrics(probability,mask)
        if any(abs(result[k]-case[k])>1e-8 for k in result): raise ValueError('Saved metric mismatch')
        grouped[row['group_id']].append(result['dice'])
    mean=float(np.mean([c['dice'] for c in cases]))
    if abs(mean-summary['final_validation']['mean_dice'])>1e-8: raise ValueError('Aggregate mismatch')
    report={'passed':True,'train_pairs':len(expected_train),'validation_pairs':len(rows),'validation_groups':len(grouped),
        'mean_dice':mean,'equal_group_weighted_dice':float(np.mean([np.mean(v) for v in grouped.values()])),
        'all_prediction_hashes_and_metrics_verified':True,'test_loaded':False,'last_sha256':summary['last_sha256']}
    save_json(run/'verification.json',report)
    output.mkdir()
    ranked=sorted(cases,key=lambda c:(c['dice'],c['path']))
    selected=[('Lowest Dice',ranked[0]),('Middle-ranked Dice',ranked[len(ranked)//2]),('Highest Dice',ranked[-1])]
    cards=[]
    for index,(name,case) in enumerate(selected):
        row,mask=by_path[case['path']]
        with Image.open(Path(config['root'])/row['path']) as image: plain=np.asarray(image.convert('RGB')).copy()
        with np.load(run/'predictions'/case['prediction'],allow_pickle=False) as saved:
            prediction=native_probability(saved['probability'],mask.shape)>=.5
        panels=[plain]
        for region in (mask>0,prediction):
            overlay=plain.copy(); overlay[region]=(.45*overlay[region]+.55*np.array([255,60,60])).astype(np.uint8)
            panels.append(overlay)
        Image.fromarray(np.concatenate(panels,axis=1)).save(output/f'example-{index}.png')
        cards.append(f'<h2>{name}: {html.escape(case["label"])} · Dice {case["dice"]:.3f}</h2><p>{html.escape(Path(case["path"]).name)}</p><p>Original image | supplied mask after documented binarization | model prediction</p><img src="example-{index}.png" style="width:100%">')
    per_class=''.join(f'<tr><td>{label}</td><td>{sum(c["label"]==label for c in cases)}</td><td>{value:.4f}</td></tr>' for label,value in summary['final_validation']['per_class_dice'].items())
    (output/'index.html').write_text(f'''<!doctype html><meta charset="utf-8"><title>Tumor segmentation results</title><style>body{{font:17px system-ui;max-width:1200px;margin:35px auto;padding:20px;color:#19384c}}td,th{{padding:10px}}.note{{background:#fff1cd;padding:16px}}</style>
<h1>First tumor-segmentation baseline</h1><p>Final epoch · {len(rows)} annotated validation images · mean original-size Dice {mean:.4f} · mean IoU {summary['final_validation']['mean_iou']:.4f}</p>
<p class="note">2D research results on tumor-positive images only. Patient independence unverified. No test evaluation. This does not measure tumor screening accuracy or physical volume.</p>
<p>Equal-group-weighted Dice {report['equal_group_weighted_dice']:.4f} across {len(grouped)} similarity groups. This is not patient-level performance.</p>
<table><tr><th>Class</th><th>Validation pairs</th><th>Mean Dice</th></tr>{per_class}</table>
<p>Gallery is selected by lowest, middle-ranked and highest Dice; it is not representative sampling.</p>{''.join(cards)}
<p><a href="../progress.html">Training history</a> · <a href="../summary.json">Summary</a> · <a href="../verification.json">Verification</a></p>''',encoding='utf-8')
    (run/'MODEL_CARD.md').write_text(f'''# BRISC 2D tumor segmentation baseline

Compact 2D U-Net, {summary['parameters']:,} parameters; seed 42; five epochs;
Adam 0.001; batch 16; BCE plus per-image soft Dice; no augmentation or pretraining.
Training pairs: {len(expected_train)}. Validation pairs: {len(rows)}.
Input: compatible 2D grayscale BRISC-style T1 image, bilinear 128x128 resize /255.
Target: supplied mask thresholded at 128 then nearest-neighbor resized.
All audited raw mask values lie in 0-10 or 246-255; the loader rejects the gap.
Output: 128x128 foreground probabilities, bilinearly restored to original dimensions
for evaluation at threshold 0.5. Output is not a physical tumor-volume estimate.

Final native-size Dice {mean:.4f}; mean IoU {summary['final_validation']['mean_iou']:.4f}.
Best mean Dice {summary['best_mean_dice']:.4f} at epoch {summary['best_epoch']}.
Saved predictions/gallery use last.pt. Test and quarantine are unused. No_tumor
images are excluded rather than assigned unsupported empty masks; negative-case
specificity is unmeasured. Patient independence and external validity are unproven.
No clinical use or general brain-abnormality detection claim. Resume not verified.
BRISC v6 CC BY 4.0 attribution is in docs/BRISC_DATASET.md.
Split hash: {config['split_sha256']}.
Last checkpoint hash: {summary['last_sha256']}.
''',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
