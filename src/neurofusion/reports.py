"""Self-contained research exports from saved predictions and review entries."""
import base64
import hashlib
from html import escape
import json
from datetime import datetime, timezone
from neurofusion.measurements import validate_evidence


def snapshot(store, job):
    if len(job) != 32 or any(c not in '0123456789abcdef' for c in job):
        raise ValueError('Invalid analysis ID')
    record = store.get(job)
    if not record or record['status'] != 'completed':
        raise ValueError('Reports require a completed analysis')
    raw = (store.root / 'results' / job / 'result.json').read_bytes()
    result_hash = hashlib.sha256(raw).hexdigest()
    reviews = store.reviews(job)
    for entry in reviews['reviews']:
        entry['matches_exported_result'] = entry['result_sha256'] == result_hash
    return {'report_schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'research_only': True, 'job': record, 'result_sha256': result_hash,
            'model_output': json.loads(raw), 'human_review': reviews,
            'scope': 'Saved research predictions and human observations; not a diagnosis or clinical report.'}


def render_html(store, report):
    """Embed selected preview PNGs so downloaded HTML works offline."""
    def e(value):
        return escape(str(value), quote=True)
    def pair(label, value):
        return f'<dt>{e(label)}</dt><dd>{e(value)}</dd>'
    result = report['model_output']; job = report['job']; reviews = report['human_review']['reviews']
    folder = (store.root / 'results' / job['id']).resolve()
    measurements=result.get('measurements')
    if measurements:validate_evidence(result,folder)
    def png(name):
        path = (folder / name).resolve()
        if path.parent != folder or path.suffix != '.png':
            raise ValueError('Invalid preview asset')
        data = path.read_bytes()
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Invalid preview PNG')
        return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')
    pieces = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'">',
              '<title>NeuroFusion research report</title><style>',
              'body{font:16px system-ui,sans-serif;color:#172b40;max-width:1000px;margin:40px auto;padding:0 24px;line-height:1.5}',
              'h1,h2{color:#11665e}h2{border-bottom:1px solid #ccd6df;padding-top:20px}.notice{border-left:4px solid #ba7c12;padding:12px;background:#fff5df}',
              'dt{font-weight:bold}dd{margin:0 0 12px;overflow-wrap:anywhere}.note{white-space:pre-wrap;overflow-wrap:anywhere}',
              'table{border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #ddd}',
              '.images{display:flex;gap:16px}.images figure{flex:1;margin:0;min-width:0}.stack{position:relative}.stack img{width:100%;display:block}.overlay{position:absolute;inset:0}',
              'article,figure{break-inside:avoid}@media print{body{margin:0;font-size:11pt}h2{break-after:avoid}.notice{border:1px solid #999}}',
              '</style></head><body><h1>NeuroFusion research report</h1>',
              '<p class="notice">Research only. Not a diagnosis. Model scores are uncalibrated; no_tumor does not mean healthy. Reviewer labels are self-entered and unverified.</p>',
              '<p>Offline snapshot. Later reviews are not included. Use your browser print command to print or save as PDF.</p><h2>Analysis and provenance</h2><dl>']
    for label, value in [('Generated (UTC)', report['generated_at']), ('Analysis ID', job['id']),
                         ('Input filename', job['filename']), ('Task', job['task']),
                         ('Analysis record timestamp (UTC)', job['created']), ('Input SHA-256', result.get('input_sha256','Unavailable')),
                         ('Result JSON SHA-256', report['result_sha256']), ('Inference device', result.get('device','Unavailable')),
                         ('Input compatibility', result.get('input_compatibility','Not verified'))]:
        pieces.append(pair(label, value))
    for name, checksum in result.get('models', {}).items():
        pieces.append(pair('Checkpoint SHA-256 / ' + name, checksum))
    pieces.append('</dl><h2>Model outputs</h2>')
    uncertainty=result.get('uncertainty')
    if uncertainty:
        pieces.append('<h3>Uncertainty decision: '+e(uncertainty['decision'])+'</h3><p class="notice">'+e(uncertainty['reason'])+'</p>')
        screen=uncertainty.get('classification_development_screen',{})
        pieces.append('<p>Classification development screen: '+e(screen.get('decision','unavailable'))+'. This does not establish independent reliability.</p>')
    else:
        pieces.append('<p class="notice">Uncertainty decision was not recorded for this older result. Reliability is not established.</p>')
    classification = result.get('classification')
    if classification:
        pieces.append('<p>Top image class: <strong>' + e(classification['predicted_class']) + '</strong>. Segmentation is an independent output.</p><table><tr><th>Class</th><th>Uncalibrated score</th></tr>')
        for label, score in classification['scores'].items():
            pieces.append(f'<tr><td>{e(label)}</td><td>{float(score)*100:.2f}%</td></tr>')
        pieces.append('</table>')
    unit = 'voxels' if job['task'] == 'stroke-dwi' else 'pixels'
    pieces.append('<p>Predicted region: ' + e(result.get('predicted_pixels_or_voxels','Unavailable')) + ' ' + unit +
                  ' at threshold ' + e(result.get('threshold','Unavailable')) + '. This is not a physical volume or disease severity score.</p>')
    if measurements:
        pieces.append('<h2>Measurements and linked evidence</h2><p>'+e(measurements['scope'])+'</p>')
        if measurements['physical_measurements_available']:
            pieces.append('<p>Total predicted volume: '+e(f"{measurements['total_volume_ml']:.4f}")+' mL. Coordinates are NIfTI RAS+ millimeters, not atlas locations.</p>')
        else:pieces.append('<p>Physical area/volume unavailable: no trusted pixel spacing. Pixel counts only.</p>')
        pieces.append('<table><tr><th>Predicted region</th><th>Size</th><th>Centroid</th><th>Evidence</th></tr>')
        for f in measurements['findings']:
            size=f"{f['volume_ml']:.4f} mL" if 'volume_ml' in f else str(f['count'])+' pixels'
            centroid=f.get('centroid_ras_mm',f['centroid_index'])
            pieces.append('<tr><td>'+e(f['id'])+'</td><td>'+e(size)+'</td><td>'+e(', '.join(f'{v:.2f}' for v in centroid))+'</td><td><a href="#preview-'+str(f['slice_index'])+'">Image / slice '+str(f['slice_index']+1)+'</a></td></tr>')
        pieces.append('</table>')
    else:pieces.append('<p>Validated measurements and finding links were not recorded for this older result.</p>')
    pieces.append('<h2>Input quality checks</h2>')
    quality=result.get('input_quality')
    if quality:
        pieces.append('<p>'+e(quality['status'])+' / policy '+e(quality['policy_version'])+'</p><p>'+e(quality['scope'])+'</p><ul>')
        for warning in quality['warnings']:
            pieces.append('<li>'+e(warning)+'</li>')
        pieces.append('</ul><dl>')
        for name,value in quality['metrics'].items(): pieces.append(pair(name,value))
        pieces.append('</dl>')
    else:
        pieces.append('<p>Not recorded for this earlier analysis. No retrospective quality claim is made.</p>')
    pieces.append('<h2>Limitations</h2><ul>')
    for limit in result.get('limitations', []):
        pieces.append('<li>' + e(limit) + '</li>')
    pieces.append('</ul><h2>Selected preview images</h2><p>Red indicates the model prediction. No reference mask is displayed. DWI previews use canonical RAS slice order and voxel-based proportions.</p>')
    views = result.get('views', [])
    selected = {result.get('initial_slice', 0)} if views else set()
    selected.update(entry['slice_index'] for entry in reviews if entry['slice_index'] is not None and entry['matches_exported_result'])
    if measurements:selected.update(f['slice_index'] for f in measurements['findings'])
    for index in sorted(selected):
        if not 0 <= index < len(views):
            raise ValueError('Invalid report slice')
        view = views[index]
        image, overlay = png(view['image']), png(view['overlay'])
        pieces.append(f'<a id="preview-{index}"></a>')
        why = 'Default model preview' if index == result.get('initial_slice',0) else 'Linked evidence or review image'
        pieces.append(f'<article><h3>Image / slice {index+1} of {len(views)} — {e(why)}</h3><div class="images"><figure><img style="width:100%" alt="Input preview" src="{image}"><figcaption>Input preview</figcaption></figure><figure><div class="stack"><img alt="Input preview" src="{image}"><img class="overlay" alt="Predicted region" src="{overlay}"></div><figcaption>Prediction overlay</figcaption></figure></div></article>')
    pieces.append('<h2>Human observations — separate from model outputs</h2><p>Entries are presented as written, without medical interpretation. Reviewed does not mean the prediction is correct. Notes are not training labels.</p>')
    if not reviews:
        pieces.append('<p>No review entries existed at export time.</p>')
    for entry in reviews:
        location = 'Whole analysis' if entry['slice_index'] is None else f"Image / slice {entry['slice_index']+1}"
        pieces.append('<article><h3>' + e(entry['reviewer']) + '</h3><p>' + e(entry['assessment']) + ' / ' + e(entry['created']) + ' / ' + e(location) + '</p><p class="note">' + e(entry['note']) + '</p>')
        if not entry['matches_exported_result']:
            pieces.append('<p class="notice">This entry refers to a different result JSON hash. Its slice link is not used for this export.</p>')
        pieces.append('<dl>' + pair('Entry ID',entry['id']) + pair('Reviewed result SHA-256',entry['result_sha256']) + '</dl></article>')
    pieces.append('<h2>Export scope</h2><p>This file includes selected preview images and review text. It does not include raw scans, full probability arrays, model weights, or an independent clinical assessment. It may contain private filenames and reviewer notes. Share only with intended recipients.</p></body></html>')
    return ''.join(pieces).encode('utf-8')
