"""Close local identity documentation without claiming unknown independence."""
import argparse
from collections import Counter,defaultdict
import json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.pdgm import read_metadata
from neurofusion.eeg import patient_group

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
sources={}
def read(name):
    path=root/name;sources[name]=digest(path);return json.loads(path.read_text(encoding='utf-8'))
def crossings(records,key):
    groups=defaultdict(set)
    for r in records:
        if r['partition']!='quarantine':groups[r[key]].add(r['partition'])
    return [{'identity':k,'partitions':sorted(v)} for k,v in groups.items() if len(v)>1]

brisc=read('experiments/brisc-curated-001/splits.json')['assignments']
edges=read('experiments/brisc-curated-001/similarity-edges.json');lookup={r['path']:r for r in brisc}
edge_conflicts=[e for e in edges if lookup[e['a']]['partition']!='quarantine' and lookup[e['b']]['partition']!='quarantine' and lookup[e['a']]['partition']!=lookup[e['b']]['partition']]
brisc_checks={key:crossings(brisc,key) for key in ('group_id','sha256','pixel_sha256')}
if any(brisc_checks.values()) or edge_conflicts:raise ValueError('BRISC active leakage detected')
isles=read('experiments/isles-curated-001/manifest.json')['studies']
splits=read('experiments/isles-curated-001/frozen-splits-v1.json')['assignments']
quarantine=read('experiments/isles-curated-001/quarantine.json')
ids={s['subject_id'] for s in isles}
if ids!=set(splits) or ids&set(quarantine['excluded_subjects']):raise ValueError('ISLES quarantine/coverage differs')
hash_groups=defaultdict(set)
for study in isles:
    for modality,f in study['files'].items():
        if modality not in ('mask','label','seg'):
            key=f.get('voxel_sha256',f.get('sha256'))
            if key:hash_groups[key].add(splits[study['subject_id']])
if any(len(v)>1 for v in hash_groups.values()):raise ValueError('ISLES cross-partition duplicate')
parts=read('experiments/ucsf-specialist-plan-001/partitions.json')['records']
acq=read('experiments/ucsf-acquisition-001/summary.json')['results']
metadata_path=root/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv'
sources[str(metadata_path.relative_to(root)).replace('\\','/')]=digest(metadata_path)
metadata=read_metadata(metadata_path);by_exam={r['exam_id']:r for r in metadata}
roles=defaultdict(set)
for r in parts:roles[r['patient_id']].add(r['role'])
for r in acq:roles[r['patient_id']].add('protected')
if any(len(v)>1 for v in roles.values()):raise ValueError('UCSF patient crosses roles')
for r in parts+acq:
    if by_exam[r['exam_id']]['patient_id']!=r['patient_id']:raise ValueError('UCSF metadata identity mismatch')
mapped=[dict(patient_id=r['patient_id'],brats21_id=by_exam[r['exam_id']]['brats21_id'],role=r.get('role','protected')) for r in parts+acq if by_exam[r['exam_id']]['brats21_id']]
historical=read('experiments/independent-evaluation-001/source-inventory.json')
for f in historical['files']:
    if digest(root/f['path'])!=f['sha256']:raise ValueError('UCSF original source changed')
comparisons=read('experiments/independent-evaluation-001/volume-comparisons.json')
flags=[r for r in comparisons['pairs'] if r['requires_review']]
eeg=read('experiments/eeg-pilot-001/download-manifest.json')['records']
eeg_roles=defaultdict(set)
for r in eeg:
    if patient_group(r['case'])!=r['patient']:raise ValueError('EEG alias mismatch')
    eeg_roles[r['patient']].add(r['partition'])
    if digest(root/'data/raw/chbmit-pilot'/r['path'])!=r['sha256']:raise ValueError('EEG file changed')
if any(len(v)>1 for v in eeg_roles.values()):raise ValueError('EEG patient crosses roles')
# Compare recorded byte hashes only; cross-modality absence is not patient evidence.
inventory=[]
for r in brisc:inventory.append(dict(dataset='BRISC',path=r['path'],sha256=r['sha256']))
for s in isles:
    for f in s['files'].values():
        if f.get('sha256'):inventory.append(dict(dataset='ISLES',path=f['path'],sha256=f['sha256']))
for f in historical['files']:inventory.append(dict(dataset='UCSF',**f))
for r in eeg:inventory.append(dict(dataset='CHB-MIT',path=r['path'],sha256=r['sha256']))
by_hash=defaultdict(list)
for r in inventory:by_hash[r['sha256']].append(r)
cross_source=[v for v in by_hash.values() if len({r['dataset'] for r in v})>1]
issues=[
 dict(id='BRISC_PATIENTS',status='documented_unresolvable_locally',finding='Publisher image/group IDs do not identify patients',disposition='Report image-group development results only; no patient-independent claim'),
 dict(id='CROSS_SOURCE_IDENTITY',status='documented_unresolvable_locally',finding='No common patient key across BRISC, ISLES, UCSF and CHB-MIT',disposition='No cross-dataset patient fusion or external-independence claim based on dataset names'),
 dict(id='TRANSFORMED_DUPLICATES',status='documented_limit',finding='2D/3D crops, registration and unpublished source mappings are not exhaustively compared',disposition='Retain unknown overlap; exact-hash/similarity negatives do not clear it'),
 dict(id='HISTORICAL_EXPOSURE',status='documented_limit',finding='Logs cannot rule out unrecorded or renamed historical data use',disposition='Do not certify protected cohort independent from all prior exposure'),
 dict(id='VALIDATION_REUSE',status='documented_known_exposure',finding='Development validation inspected repeatedly during experiments',disposition='Calibration and model selection remain development-only'),
 dict(id='ISLES_DUPLICATES',status='resolved_by_existing_quarantine',finding='0090 and 0169 share image content with discrepant annotation history',disposition='Both excluded from current 248-study manifest; no changes to partition'),
 dict(id='EEG_ALIAS',status='resolved_in_local_identity_policy',finding='chb21 aliases chb01; chb21 is absent from the 12-recording pilot',disposition='Canonical patient grouping verified; never treat chb21 as an additional patient'),
 dict(id='UCSF_BRATS',status='documented_known_mapping',finding='Local publisher metadata contains BraTS mappings',disposition='Mappings retained explicitly; protected patients checked for mappings; absent mapping is not proof of no overlap')]
summary=dict(documentation_complete=True,independence_certified=False,partitions_changed=False,test_inference=False,downloads=0,
    brisc=dict(images=len(brisc),partitions=dict(Counter(r['partition'] for r in brisc)),active_crossings=brisc_checks,similarity_edges_checked=len(edges),edge_conflicts=edge_conflicts,patient_identity_verified=False),
    isles=dict(retained_patients=len(ids),partitions=dict(Counter(splits.values())),quarantined=quarantine['excluded_subjects'],cross_partition_recorded_hash_conflicts=0),
    ucsf=dict(development_patients=len(parts),protected_patients=len(acq),metadata_identity_matches=len(parts)+len(acq),source_files_rehashed=len(historical['files']),known_mappings=mapped,prior_similarity_pairs=len(comparisons['pairs']),prior_similarity_flags=flags),
    eeg=dict(recordings=len(eeg),canonical_patients=len(eeg_roles),patient_role_conflicts=0),
    cross_dataset_recorded_file_hash_matches=cross_source,recorded_file_hashes_compared=len(inventory),
    limitations='BRISC/ISLES file hashes are recorded manifest evidence, not a fresh pixel/source rescan. UCSF/EEG sources rehashed. Prior similarity screen retained, not newly recomputed.',issues=issues)
save_json(a.output/'summary.json',summary);save_json(a.output/'evidence-hashes.json',sources)
save_json(a.output/'issue-register.json',issues)
print(json.dumps(summary,indent=2))
