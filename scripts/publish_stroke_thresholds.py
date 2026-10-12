"""Append the complete exploratory threshold grid to the quality report."""
import json
from pathlib import Path
from neurofusion.data import save_json
from neurofusion.external_import import digest

root=Path(__file__).resolve().parents[1];source=root/'experiments/stroke-threshold-001'
destination=root/'experiments/model-quality-001';target=destination/'stroke-thresholds.json'
if target.exists():raise ValueError('Threshold publication exists')
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
summary=read(source/'summary.json');protocol=read(source/'protocol.json')
if summary['protocol_sha256']!=digest(source/'protocol.json'):raise ValueError('Protocol changed')
save_json(target,{'protocol':protocol,**summary})
rows=''.join(f'<tr><td>{r["threshold"]:.2f}</td><td>{r["candidate"]["mean_dice"]:.4f}</td><td>{r["candidate"]["mean_absolute_volume_error_ml"]:.4f}</td><td>{r["candidate"]["lesion_recall"]:.4f}</td><td>{r["candidate"]["lesion_precision"]:.4f}</td><td>{sum(r["checks"].values())}/6</td></tr>' for r in summary['results'])
section=f'<section><h2>Stroke: exploratory threshold development</h2><p>Preselected grid: 0.55, 0.65, 0.75. Selected threshold: {summary["selected_threshold"]}. Comparisons use the original epoch-5 threshold-0.5 baseline. Threshold tuning reuses development data; this is not independent qualification. The original epoch-10 threshold-0.5 failure remains above. No active model changed. Zero-Dice cases increase from 4 to 6 at threshold 0.65; this regression is outside the six predeclared checks and needs review.</p><table><tr><th>Threshold</th><th>Dice</th><th>Volume error mL</th><th>Recall</th><th>Precision</th><th>Checks</th></tr>{rows}</table><p><a href="stroke-thresholds.json">All results and selection protocol</a></p></section>'
page=destination/'index.html'
page.write_text(page.read_text(encoding='utf-8').replace('</html>',section+'</html>'),encoding='utf-8')
print('Published all threshold outcomes')
