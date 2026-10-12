"""Create a reproducible reference audit and pending human-review ledger."""
import hashlib
import html
import json
import os
from pathlib import Path
from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.exposure import reference_hits
from neurofusion.pdgm import read_metadata

root=Path(__file__).resolve().parents[1]
out=root/'experiments/ucsf-exposure-001'
if out.exists(): raise ValueError('Fresh snapshot required')
acq=root/'experiments/ucsf-acquisition-001'
summary=json.loads((acq/'summary.json').read_text())
assert summary['verified_pairs']==20 and summary['failed_pairs']==0
patients={r['patient_id'] for r in summary['results']}
hashes={}
for row in summary['results']:
    for f in row['files']:
        p=(acq/f['path']).resolve()
        if not p.is_relative_to(acq.resolve()) or digest(p)!=f['sha256']:
            raise ValueError('Acquisition file changed or escaped root')
        hashes.setdefault(f['sha256'],[]).append(row['patient_id'])
metadata=read_metadata(root/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv')
dev=json.loads((root/'data/ucsf-import-manifest.json').read_text())['records']
assert not patients.intersection(r['patient_id'] for r in dev)
assert not patients.intersection(r['patient_id'] for r in metadata if r['brats21_id'])
# These directories contain inventory/intake evidence, not training declarations.
inventory_prefixes=('experiments/pdgm-intake-001/', 'experiments/pdgm-cohort-separation-001/',
    'experiments/ucsf-qualification-001/', 'experiments/ucsf-acquisition-001/',
    'data/downloads/ucsf-pdgm-v5-metadata/')
extensions={'.json','.jsonl','.csv','.yaml','.yml','.md','.py','.txt','.log'}
files=[]; skipped=[]; hits=[]
for base in ('configs','experiments','scripts','src','data'):
    for directory, dirs, names in os.walk(root/base):
        # Pixel arrays/checkpoints cannot be searched as text. Explicit exclusions
        # keep the scope reproducible and prevent scanning the acquired raw data.
        dirs[:]=sorted(d for d in dirs if d not in
            {'raw','__pycache__','.git','node_modules','ucsf-exposure-001'})
        for name in sorted(names):
            p=Path(directory)/name
            if p.suffix.lower() not in extensions: continue
            rel=p.relative_to(root).as_posix()
            if p.stat().st_size>20_000_000:
                skipped.append({'path':rel,'reason':'over 20 MB text scan limit'});continue
            try:
                data=p.read_bytes(); text=data.decode('utf-8-sig')
            except (OSError,UnicodeError) as error:
                skipped.append({'path':rel,'reason':type(error).__name__});continue
            files.append({'path':rel,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
            matches=reference_hits(text,patients,hashes)
            if matches:
                kind='inventory_or_intake' if rel.startswith(inventory_prefixes) else 'unclassified_requires_review'
                hits.append({'path':rel,'patients':matches,'classification':kind})
out.mkdir()
ledger=[]
for row in summary['results']:
    patient=row['patient_id']; refs=[h for h in hits if patient in h['patients']]
    exams=[r['exam_id'] for r in metadata if r['patient_id']==patient]
    image,mask=row['files']
    ledger.append({'patient_id':patient,'exam_id':row['exam_id'],'all_metadata_exam_ids':exams,
        'development_identity_overlap':False,'recorded_brats_mapping':False,
        'exact_duplicate_check':'passed in acquisition snapshot',
        'references':refs,'independence_verified':False,
        'review':{'decision':'pending','reviewer_name':None,'reviewer_qualification':None,
            'reviewed_at':None,'notes':None,'whole_volume_reviewed':False,
            'identity_checked':False,'orientation_checked':False,'alignment_checked':False,
            'image_path':(Path('../ucsf-acquisition-001')/image['path']).as_posix(),
            'mask_path':(Path('../ucsf-acquisition-001')/mask['path']).as_posix(),
            'image_sha256':image['sha256'],'mask_sha256':mask['sha256']}})
unclassified=[h for h in hits if h['classification']=='unclassified_requires_review']
result={'stage':'Exposure audit and human review preparation','patients_audited':len(ledger),
    'text_files_scanned':len(files),'skipped_text_files':skipped,
    'reference_files':len(hits),'unclassified_reference_files':len(unclassified),
    'expert_reviews_completed':0,'independence_verified':False,'cohort_frozen':False,
    'model_inference_performed':False,'qualification_gates_passed':2,'qualification_gates_total':10,
    'scope':'UTF-8 text records in configs, experiments, scripts, src and data; raw directories and binary contents excluded; 20 MB per-file limit.',
    'limitations':['References are not proof of training exposure; absence is not proof of independence.',
        'Unlogged historical runs, renamed cases, binary-embedded IDs, near-duplicates and unknown source mappings are not ruled out.',
        'The same UCSF source does not establish external-site validation.',
        'Expert review, model qualification and a frozen evaluation protocol remain required.']}
save_json(out/'summary.json',result)
save_json(out/'exposure-ledger.json',{'records':ledger})
save_json(out/'scan-inventory.json',{'files':files,'skipped':skipped,'hits':hits})
save_json(out/'review-template.json',{'schema_version':1,'purpose':'Copy to a new review submission; never overwrite the evidence snapshot. Validate hashes against the acquisition inventory before accepting a submitted review.','records':[{'patient_id':r['patient_id'],'exam_id':r['exam_id'],**r['review']} for r in ledger]})
save_json(out/'provenance.json',{'inputs':{p:digest(root/p) for p in
    ['experiments/ucsf-acquisition-001/summary.json','experiments/ucsf-acquisition-001/qualification.json',
     'data/ucsf-import-manifest.json','data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv',
     'scripts/build_ucsf_exposure.py','src/neurofusion/exposure.py']}})
rows=''.join('<tr><td>'+html.escape(r['patient_id'])+'</td><td>'+str(len(r['references']))+'</td><td>Pending</td></tr>' for r in ledger)
out.joinpath('index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UCSF exposure and review ledger</title><style>body{font:17px system-ui;max-width:1000px;margin:30px auto;padding:20px;background:#101e2c;color:#eee}a{color:#80ded0}td,th{padding:10px;border-bottom:1px solid #567;text-align:left}progress{width:100%;height:26px}</style>'
    '<h1>Exposure audit and review preparation</h1><h2>Technical audit: 20/20 records</h2><progress max="20" value="20"></progress>'
    f'<p>{len(files)} text files scanned; {len(skipped)} skipped; {len(unclassified)} matching files require classification. See the scan inventory for exact scope.</p>'
    '<h2>Expert alignment review: 0/20</h2><progress max="20" value="0"></progress><p>All reviews remain pending. A record or file reference does not prove training exposure or independence.</p>'
    '<h2>UCSF qualification: 2/10 gates</h2><progress max="10" value="2"></progress><p>This stage prepares evidence; it does not certify cohort independence, improve model accuracy, or complete the whole project.</p>'
    '<h2>Review procedure</h2><ol><li>Open the paired original NIfTI files from the review template in a local volume viewer; verify their SHA256 values against the acquisition snapshot.</li><li>Check patient identity, orientation, spacing and image/mask alignment through the whole volume in all three planes, with overlays on and off. Sparse screenshots are insufficient.</li><li>Record accept, exclude, or needs_followup with reviewer name, qualification, timezone-aware date and notes. Use numeric labels; do not infer certified compartment meanings.</li><li>Save a separate review submission. Do not train, tune, or run predictions on these provisional cases.</li></ol>'
    '<table><tr><th>Patient</th><th>Reference files</th><th>Expert review</th></tr>'+rows+'</table>'
    '<p><a href="exposure-ledger.json">Exposure ledger</a> · <a href="review-template.json">Review template</a> · <a href="scan-inventory.json">Scan inventory</a> · <a href="summary.json">Summary</a></p></html>',encoding='utf-8')
print(json.dumps(result,indent=2))
