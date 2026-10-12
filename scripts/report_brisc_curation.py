"""Render the saved classification curation outcome without training a model."""
import json
import html
from pathlib import Path

folder=Path('experiments/brisc-curated-001')
summary=json.loads((folder/'summary.json').read_text())
rows=''.join(f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>' for k,v in sorted(summary['class_counts'].items()))
page=f'''<!doctype html><meta charset="utf-8"><title>NeuroFusion tumor data readiness</title>
<style>body{{font:17px system-ui;max-width:1000px;margin:40px auto;padding:20px;color:#183445}}td{{padding:8px;border-bottom:1px solid #ddd}}progress{{width:100%;height:25px}}.note{{background:#fff1cd;padding:18px}}</style>
<h1>NeuroFusion · tumor classification data</h1>
<p>Full platform: approximately 35% — a rough scope estimate, not model accuracy.</p><progress value="35" max="100"></progress>
<p>Classification dataset preparation: complete. Tumor model training: next.</p>
<p class="note">Image-similarity groups are not patient identities. No tumor model has been trained. The segmentation masks need an explicit encoding policy before training.</p>
<h2>Frozen partitions</h2><table>{rows}</table>
<p>{summary['groups']} image groups; no active group crosses partitions. Quarantine preserves source files and excludes affected records from training.</p>
<p>{summary['masks_checksum_verified']} mask files passed publisher checksums; {summary['masks_with_intermediate_values']} contain intermediate grayscale values.</p>
<p><a href="summary.json">Full summary</a> · <a href="splits.json">Frozen image-group partitions</a> · <a href="../brisc-audit-001/index.html">Original audit and image examples</a></p>'''
output=folder/'index.html'
if output.exists(): raise ValueError('Report already exists')
output.write_text(page,encoding='utf-8')
print(output)
