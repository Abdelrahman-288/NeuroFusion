"""Audit every indexed study without hiding failures; create draft partitions only if all pass."""
import argparse
import csv
import json
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor

from neurofusion.data import audit, build_manifest, save_json, split_patients


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dataset-id',required=True)
    parser.add_argument('--workers',type=int,choices=[1,2,3],default=2)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory')
    args.output.mkdir(parents=True)
    with args.index.open(newline='',encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    valid, errors = [], []
    def inspect(row):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory)/'index.csv'
            with index.open('w',newline='',encoding='utf-8') as stream:
                writer = csv.DictWriter(stream,fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            try:
                manifest = build_manifest(index,args.root,args.dataset_id)
                return manifest['studies'][0], None
            except (ValueError,OSError) as error:
                return None, {'subject':row['subject_id'],'study':row['study_id'],'error':str(error)}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,(study,error) in enumerate(pool.map(inspect, rows)):
            if error:
                errors.append(error)
            else:
                valid.append(study)
            if (i+1)%10 == 0:
                print(f'Inspected {i+1}/{len(rows)} studies; failures: {len(errors)}',flush=True)
    report = {'indexed':len(rows),'valid':len(valid),'errors':errors,
              'geometry_warning_studies':sum(bool(s['warnings']) for s in valid),
              'status':'automated checks only; visual QC and split distribution review pending'}
    save_json(args.output/'qc-summary.json',report)
    if errors or not valid:
        print(json.dumps(report,indent=2))
        return 1
    manifest = {'schema_version':1,'dataset_id':args.dataset_id,
                'data_root':str(args.root.resolve()),'studies':valid}
    save_json(args.output/'manifest.json',manifest)
    splits = split_patients(manifest)
    result = audit(manifest,splits)
    save_json(args.output/'leakage-audit.json',result)
    if result['passed']:
        save_json(args.output/'draft-splits.json',splits)
    print(json.dumps({**report,'leakage_passed':result['passed'],'patient_counts':result['patient_counts']},indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
