"""Inventory patient exclusions without freezing a test cohort or performing inference."""
import argparse
import hashlib
import json
from pathlib import Path
from neurofusion.pdgm import read_metadata
from neurofusion.cohort_separation import audit_separation


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    records=read_metadata(args.metadata)
    manifest=json.loads(args.manifest.read_text())['records']
    by_exam={r['exam_id']:r for r in records}
    if len({r['exam_id'] for r in manifest}) != len(manifest):
        raise ValueError('Duplicate development manifest IDs')
    for row in manifest:
        if row['exam_id'] not in by_exam or by_exam[row['exam_id']]['patient_id'] != row['patient_id']:
            raise ValueError('Development manifest identity does not match metadata')
    result=audit_separation(records,[r['exam_id'] for r in manifest])
    result['source_sha256']={name:hashlib.sha256(path.read_bytes()).hexdigest()
                             for name,path in [('metadata',args.metadata),('development_manifest',args.manifest)]}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.output/'candidate-inventory.json').write_text(json.dumps({
        'purpose':'Acquisition planning only; not a frozen evaluation cohort',
        'independence_verified':False,'patients':[r for r in result['patients'] if r['candidate']]},indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='patients'},indent=2))


if __name__=='__main__':
    main()
