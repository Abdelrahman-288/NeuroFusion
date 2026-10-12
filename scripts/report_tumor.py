"""Verify completed tumor run and render final-checkpoint metrics and selected errors."""
import argparse
from collections import Counter,defaultdict
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.tumor import CLASSES,classification_metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args(); run=args.run
    output=run/'report'
    if output.exists(): parser.error('Report already exists')
    config=json.loads((run/'config.json').read_text())
    summary=json.loads((run/'summary.json').read_text())
    predictions=json.loads((run/'validation-predictions.json').read_text())
    coverage=json.loads((run/'coverage.json').read_text())
    history=json.loads((run/'history.json').read_text())
    if digest(Path(config['split_path']))!=config['split_sha256']: raise ValueError('Split changed')
    splits=json.loads(Path(config['split_path']).read_text())
    expected={r['path']:r for r in splits['assignments'] if r['partition']=='validation'}
    expected_train=[r['path'] for r in splits['assignments'] if r['partition']=='train']
    if Counter(p['path'] for p in predictions)!=Counter({p:1 for p in expected}): raise ValueError('Prediction coverage mismatch')
    if Counter(coverage['train_paths'])!=Counter(expected_train): raise ValueError('Training coverage mismatch')
    if coverage['test_loaded'] or summary['test_evaluated']: raise ValueError('Test usage unexpected')
    if any(h['train_images_seen']!=len(expected_train) for h in history) or len(history)!=config['epochs']: raise ValueError('Epoch coverage mismatch')
    if digest(run/'last.pt')!=summary['last_checkpoint_sha256']: raise ValueError('Checkpoint changed')
    labels=[]; probabilities=[]; grouped=defaultdict(list)
    for row in predictions:
        source=expected[row['path']]
        if source['label']!=row['reference'] or source['group_id']!=row['group_id']: raise ValueError('Reference/group mismatch')
        if row['predicted']!=CLASSES[int(np.argmax(row['probabilities']))]: raise ValueError('Prediction label mismatch')
        labels.append(CLASSES.index(row['reference'])); probabilities.append(row['probabilities'])
        grouped[row['group_id']].append(int(row['reference']==row['predicted']))
    score=classification_metrics(labels,probabilities)
    for key in ['accuracy','macro_f1','balanced_accuracy']:
        if abs(score[key]-summary['final_validation'][key])>1e-9: raise ValueError('Metric mismatch')
    output.mkdir()
    verification={'passed':True,'validation_images':len(predictions),'validation_groups':len(grouped),
        'equal_group_weighted_image_accuracy':float(np.mean([np.mean(v) for v in grouped.values()])),
        'test_loaded':False,'last_checkpoint_sha256':summary['last_checkpoint_sha256'],
        'limitations':'Grouping is image similarity, not verified patient identity.'}
    save_json(run/'verification.json',verification)
    errors=sorted([r for r in predictions if r['reference']!=r['predicted']],key=lambda r:-max(r['probabilities']))[:8]
    cards=[]
    for i,row in enumerate(errors):
        source=Path(config['root'])/row['path']
        if digest(source)!=expected[row['path']]['sha256']: raise ValueError('Image changed')
        with Image.open(source) as image: image.convert('RGB').save(output/f'error-{i}.png')
        cards.append(f'<div><img src="error-{i}.png" width="210"><p>Reference: {html.escape(row["reference"])}<br>Predicted: {html.escape(row["predicted"])}<br>Top softmax score: {max(row["probabilities"]):.3f}</p></div>')
    table=''.join(f'<tr><td>{r["class"]}</td><td>{r["support"]}</td><td>{r["precision"]:.3f}</td><td>{r["recall"]:.3f}</td><td>{r["f1"]:.3f}</td></tr>' for r in score['per_class'])
    confusion=''.join('<tr><th>'+CLASSES[i]+'</th>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for i,row in enumerate(score['confusion_matrix']))
    page=f'''<!doctype html><meta charset="utf-8"><title>NeuroFusion tumor baseline</title><style>body{{font:17px system-ui;max-width:1100px;margin:30px auto;padding:20px;color:#19384c}}td,th{{padding:10px;border-bottom:1px solid #ddd}}.cards{{display:flex;flex-wrap:wrap;gap:22px}}.note{{background:#fff1cd;padding:18px}}</style>
<h1>First BRISC tumor classifier</h1><p>Final checkpoint · epoch 5 · {len(predictions)} validation images · test partition unused</p>
<p class="note">Research image-level results. Patient independence is unverified. No_tumor is not healthy. Softmax scores are uncalibrated. This classifier does not produce tumor masks.</p>
<p>Accuracy <b>{score['accuracy']:.1%}</b> · Macro F1 <b>{score['macro_f1']:.3f}</b> · Balanced accuracy <b>{score['balanced_accuracy']:.1%}</b></p>
<p>Equal-group-weighted image accuracy: {verification['equal_group_weighted_image_accuracy']:.1%} across {len(grouped)} similarity groups. This is a supplementary weighting check, not patient-level performance.</p>
<h2>Per-class results</h2><table><tr><th>Class</th><th>Images</th><th>Precision</th><th>Recall</th><th>F1</th></tr>{table}</table>
<h2>Confusion matrix</h2><p>Rows: reference; columns: prediction.</p><table><tr><th></th>{''.join('<th>'+c+'</th>' for c in CLASSES)}</tr>{confusion}</table>
<h2>Selected mistakes</h2><p>Up to eight errors with the largest top softmax score. Deliberately selected failures, not a representative sample.</p><div class="cards">{''.join(cards)}</div>
<p><a href="../progress.html">Training history</a> · <a href="../summary.json">Full metrics</a> · <a href="../verification.json">Verification</a></p>'''
    (output/'index.html').write_text(page,encoding='utf-8')
    (run/'MODEL_CARD.md').write_text(f'''# BRISC compact tumor CNN

Research baseline trained from scratch; {summary['parameters']:,} parameters.
Input: one compatible 2D BRISC-style T1 image, converted to grayscale, resized to
128x128 with bilinear interpolation and scaled by 255. Output order: {', '.join(CLASSES)}.
Five epochs, seed {config["seed"]}, Adam 0.001, batch 32, cross entropy, no pretraining. Training augmentation: {config.get("augmentation") or "none"}.
Training: {summary['train_images']} images. Validation: {summary['validation_images']} images.
Final accuracy {score['accuracy']:.4f}, macro F1 {score['macro_f1']:.4f}, balanced accuracy {score['balanced_accuracy']:.4f}.
Best validation macro F1 {summary['best_macro_f1']:.4f} at epoch {summary['best_epoch']}.
Prediction JSON and report correspond to last.pt, not necessarily best.pt.

Test/quarantine images were not loaded. Patient independence is unverified and
source collection bias/near-duplicate leakage remain possible. Repeated images
within similarity groups can overweight groups; the report includes an equal-group
weighting check. No_tumor is not a general healthy-brain class. Softmax scores are
uncalibrated. No segmentation, external validation, clinical validation or uncertainty
estimation is provided. Model is not ready for diagnostic decisions.

Source dataset: BRISC v6, CC BY 4.0; see docs/BRISC_DATASET.md for attribution.
Split SHA256: {config['split_sha256']}.
Last checkpoint SHA256: {summary['last_checkpoint_sha256']}.
Training/checkpoint resume is not yet verified for this new classifier.
''',encoding='utf-8')
    print(json.dumps({**score,**verification},indent=2))


if __name__=='__main__': main()
