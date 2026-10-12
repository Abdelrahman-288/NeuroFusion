"""Audit local UCSF comparison content and prepare blocked evaluation handoff."""
import hashlib
import json
from pathlib import Path
import sqlite3
import nibabel as nib
import numpy as np
from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.exposure import reference_hits
from neurofusion.pdgm import read_metadata
from neurofusion.volume_similarity import fingerprint,similarity

root=Path(__file__).resolve().parents[1];out=root/'experiments/independent-evaluation-001'
if out.exists():raise ValueError('Fresh evidence directory required')
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
acq=root/'experiments/ucsf-acquisition-001';inventory=read(acq/'summary.json')
development=read(root/'data/ucsf-import-manifest.json')['records']
metadata=read_metadata(root/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv')
out.mkdir()
save_json(out/'audit-protocol.json',{'scope':'20 provisional UCSF pairs versus 20 locally recorded UCSF development pairs; image-only similarity screen',
    'similarity':'Canonical RAS image, linear 24-cubed thumbnail, nonzero intensity z-score, normalized dot product',
    'flag_threshold':.995,'decision':'Flags require review; no flags do not prove independence',
    'limitations':['No registration or crop search','No comparison to unrecorded or unavailable source data','Same-source rather than external-site evaluation'],
    'model_inference_permitted':False,'cohort_selection_changes_permitted':False})
records=[];fingerprints={};hash_inventory=[]
for group,rows in [('development',development),('provisional',inventory['results'])]:
    for row in rows:
        if group=='development':
            files=[{'path':row[k]['path'],'sha256':row[k]['sha256']} for k in ('image','mask')]
            base=root/'data/raw/ucsf-pdgm-v5'
        else:files=row['files'];base=acq
        paths=[]
        for f in files:
            path=(base/f['path']).resolve()
            if not path.is_relative_to(base.resolve()) or digest(path)!=f['sha256']:raise ValueError('Source changed or escaped root')
            paths.append(path);hash_inventory.append({'path':path.relative_to(root).as_posix(),'sha256':f['sha256']})
        volume=nib.as_closest_canonical(nib.load(paths[0]));values=volume.get_fdata(dtype=np.float32)
        h=hashlib.sha256(str(values.shape).encode());h.update(np.asarray(values,dtype='<f4').tobytes())
        key=group+'/'+row['exam_id'];fingerprints[key]=fingerprint(values)
        records.append({'key':key,'group':group,'exam_id':row['exam_id'],'patient_id':row['patient_id'],
                        'shape':list(values.shape),'canonical_voxel_sha256':h.hexdigest()})
        print('Audited '+key,flush=True)
pairs=[]
for i,a in enumerate(records):
    for b in records[:i]:
        if a['group']==b['group']=='development':continue
        score=similarity(fingerprints[a['key']],fingerprints[b['key']])
        exact=a['canonical_voxel_sha256']==b['canonical_voxel_sha256']
        pairs.append({'left':a['key'],'right':b['key'],'similarity':score,'exact_voxel_duplicate':exact,'requires_review':exact or score>=.995})
patients={r['patient_id'] for r in inventory['results']};dev_ids={r['patient_id'] for r in development}
mapped={r['patient_id'] for r in metadata if r['brats21_id']}
# Scan all currently recorded experiment configurations, including ignored files.
configs=[];hits=[]
for path in sorted((root/'experiments').rglob('config.json')):
    data=path.read_text(encoding='utf-8-sig');matches=reference_hits(data,patients,{})
    record={'path':path.relative_to(root).as_posix(),'sha256':digest(path),'matches':matches}
    configs.append(record)
    if matches:hits.append(record)
db=root/'experiments/local-viewer/cohort-review/reviews.sqlite3'
reviews=[]
if db.exists():
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as connection:
        reviews=[json.loads(r[0]) for r in connection.execute('SELECT payload FROM cohort_reviews ORDER BY exam, revision')]
flags=[p for p in pairs if p['requires_review']]
result={'provisional_pairs':len(patients),'development_pairs':len(development),'source_files_verified':len(hash_inventory),
        'comparisons':len(pairs),'similarity_flags':flags,'known_patient_overlap':sorted(patients&dev_ids),
        'recorded_brats_overlap':sorted(patients&mapped),'experiment_configs_scanned':len(configs),'config_reference_flags':hits,
        'local_review_submissions':len(reviews),'qualified_expert_reviews_completed':0,
        'independence_verified':False,'cohort_frozen':False,'model_inference_performed':False,
        'expert_review_required':False,
        'blockers':['Unlogged and unknown cross-source exposure not ruled out',
                    'UCSF specialist development performance gate failed','Target contract and candidate-specific acceptance criteria not approved'],
        'note':'BRISC tumor and ISLES stroke results do not qualify the different UCSF specialist or make this a stroke cohort.'}
save_json(out/'summary.json',result)
save_json(out/'volume-comparisons.json',{'records':records,'pairs':pairs})
save_json(out/'source-inventory.json',{'files':hash_inventory,'experiment_configs':configs,
    'acquisition_manifest_sha256':digest(acq/'summary.json'),'development_manifest_sha256':digest(root/'data/ucsf-import-manifest.json'),
    'metadata_sha256':digest(root/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv'),'script_sha256':digest(Path(__file__))})
save_json(out/'review-snapshot.json',{'submissions':reviews,'reviewer_credentials_verified':False,'user_reports_no_reviewer':True})
save_json(out/'evaluation-protocol-draft.json',{'status':'DRAFT_NOT_FROZEN','task':'UCSF T1c MRI numeric annotation union segmentation',
    'target':'supplied labels 1, 2, 4 as foreground; no named-compartment claim',
    'cohort_manifest_sha256':digest(acq/'summary.json'),'provisional_patients':sorted(patients),'candidate_checkpoint_sha256':None,
    'preprocessing_version':None,'threshold':None,'acceptance_criteria':None,'cohort_exclusions':None,
    'proposed_reporting':['All eligible patients and exclusions with reasons','Native-volume Dice and IoU','False-positive volume mL',
                          'Absolute volume error mL','Zero-Dice and empty-output counts','Patient bootstrap confidence intervals'],
    'expert_review_required':False,
    'freeze_requires':['Qualified model with development-only checkpoint selection',
                       'Resolved independence findings and documented scope','Approved target, preprocessing, threshold, acceptance criteria and statistical plan'],
    'execution_permitted':False,'rule':'No model inference, selection, or threshold tuning on this cohort before prerequisites and immutable freeze.'})
print(json.dumps(result,indent=2))
