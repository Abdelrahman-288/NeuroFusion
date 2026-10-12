"""Conservatively exclude every subject in an exact-image duplicate group.

Source data and original manifest are preserved. This does not adjudicate patient
identity or select a preferred annotation. Exclusions require later review.
"""
import argparse
import hashlib
import json
from pathlib import Path

from neurofusion.data import MODALITIES, audit, save_json, split_patients


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory')
    original=args.manifest.read_bytes()
    manifest=json.loads(original)
    hashes={}
    for study in manifest['studies']:
        for modality in MODALITIES:
            signature=study['files'][modality]['voxel_sha256']
            hashes.setdefault(signature,[]).append({'subject':study['subject_id'],'study':study['study_id'],'modality':modality})
    groups=[{'voxel_sha256':key,'members':members} for key,members in hashes.items()
            if len({m['subject'] for m in members})>1]
    excluded=sorted({m['subject'] for group in groups for m in group['members']})
    manifest['studies']=[s for s in manifest['studies'] if s['subject_id'] not in excluded]
    manifest['curation']={'source_manifest_sha256':hashlib.sha256(original).hexdigest(),
                          'excluded_subjects':excluded,'reason':'All subjects sharing exact image content quarantined pending identity/annotation review'}
    splits=split_patients(manifest)
    report=audit(manifest,splits)
    if not report['passed']:
        raise ValueError(report['errors'])
    save_json(args.output/'quarantine.json',{'groups':groups,**manifest['curation'],
              'raw_files_modified':False,'retained_studies':len(manifest['studies'])})
    save_json(args.output/'manifest.json',manifest)
    save_json(args.output/'draft-splits.json',splits)
    save_json(args.output/'leakage-audit.json',report)
    print(json.dumps({'excluded_subjects':excluded,'retained_studies':len(manifest['studies']),
                      'audit_passed':report['passed'],'patient_counts':report['patient_counts']},indent=2))


if __name__=='__main__':
    main()
