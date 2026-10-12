"""Verify identity disposition closure without promoting independence claims."""
import json
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json

root=Path(__file__).resolve().parents[1];run=root/'experiments/data-independence-closure-001'
read=lambda p:json.loads(p.read_text())
summary=read(run/'summary.json');hashes=read(run/'evidence-hashes.json')
for name,expected in hashes.items():
    if digest(root/name)!=expected:raise ValueError('Audit evidence changed: '+name)
issues=read(run/'issue-register.json')
if issues!=summary['issues'] or len({r['id'] for r in issues})!=len(issues):raise ValueError('Issue register differs')
if any(not all(r.get(k) for k in ('id','status','finding','disposition')) for r in issues):raise ValueError('Missing disposition')
if summary['independence_certified'] or summary['partitions_changed'] or summary['test_inference'] or summary['downloads']:
    raise ValueError('Invalid closure claim')
if any(summary['brisc']['active_crossings'].values()) or summary['brisc']['edge_conflicts']:raise ValueError('BRISC conflict')
if any(r['role']=='protected' for r in summary['ucsf']['known_mappings']):raise ValueError('Protected cohort has recorded BraTS mapping')
if summary['cross_dataset_recorded_file_hash_matches']:raise ValueError('Cross-source byte matches need disposition')
old_verification=read(root/'experiments/independent-evaluation-001/verification.json')
for name in ('volume-comparisons.json','source-inventory.json'):
    if digest(root/'experiments/independent-evaluation-001'/name)!=old_verification['artifact_sha256'][name]:raise ValueError('Historical similarity evidence changed')
out=run/'verification.json'
if out.exists():raise ValueError('Verification already exists')
save_json(out,dict(passed=True,evidence_files_checked=len(hashes),issues_with_dispositions=len(issues),
    historical_similarity_artifacts_verified=True,documentation_complete=True,
    independence_certified=False,summary_sha256=digest(run/'summary.json')))
print(out.read_text())
