"""Run annotation roundtrip QA on an already imported, checksum-verified pilot."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--import-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = args.import_dir/'import-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    imported = json.loads((args.import_dir/'summary.json').read_text())
    records = manifest['records']
    ids = [r['exam_id'] for r in records]
    if len(set(ids)) != len(ids) or set(ids) != {
            r['exam_id'] for r in imported['results'] if r['status'] == 'prepared_requires_review'}:
        raise ValueError('Manifest must match the prepared import exactly')
    if imported['failed'] or imported['awaiting_files'] or not records:
        raise ValueError('Complete the pilot import before cohort QA')
    paths = {}
    for record in records:
        pair = []
        for role in ('image', 'mask'):
            path = (root/record[role]['path']).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Source path escapes dataset root')
            if hashlib.sha256(path.read_bytes()).hexdigest() != record[role]['sha256']:
                raise ValueError('Source checksum mismatch')
            pair.append(path)
        paths[record['exam_id']] = pair
    args.output.mkdir(parents=True, exist_ok=False)
    protocol = {'purpose': 'development annotation QA; not model performance',
                'sizes': [128, 240, 256], 'exam_ids': ids,
                'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                'model_inference_performed': False, 'evaluation_ready': False,
                'label_semantics_verified': False}
    (args.output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    cases = []
    for index, exam in enumerate(ids, 1):
        image, mask = paths[exam]
        # Numeric output directories avoid interpreting exam identifiers as paths.
        directory = args.output/f'case-{index:02d}'
        subprocess.run([sys.executable, str(Path(__file__).with_name('audit_pdgm_resolution.py')),
                        '--image', str(image), '--mask', str(mask), '--output', str(directory)],
                       check=True, stdout=subprocess.DEVNULL)
        result = json.loads((directory/'summary.json').read_text())
        record = records[index-1]
        for role in ('image', 'mask'):
            if result['source_sha256'][role] != record[role]['sha256']:
                raise ValueError('Source changed between validation and audit')
        cases.append({'exam_id': exam, 'report': f'{directory.name}/summary.json',
                      'sizes': result['sizes']})
        print(f'{index}/{len(ids)} completed: {exam}', flush=True)
    aggregate = []
    for size in protocol['sizes']:
        rows = [next(s for s in c['sizes'] if s['size'] == size) for c in cases]
        labels = [v for row in rows for v in row['labels']]
        aggregate.append({'size': size, 'exams': len(rows),
            'exams_with_component_loss': sum(any(v['components_without_same_label_overlap'] for v in row['labels']) for row in rows),
            'components_without_same_label_overlap': sum(v['components_without_same_label_overlap'] for v in labels),
            'lost_label_slices': sum(len(row['lost_label_slices']) for row in rows),
            'by_label': [{
                'label_id': label,
                'contributing_exams': len(values := [v for v in labels if v['label_id'] == label]),
                'mean_case_roundtrip_dice': sum(v['roundtrip_dice'] for v in values)/len(values),
                'minimum_case_roundtrip_dice': min(v['roundtrip_dice'] for v in values),
            } for label in sorted({v['label_id'] for v in labels})]})
    summary = {**protocol, 'completed_exams': len(cases), 'aggregate': aggregate, 'cases': cases}
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(aggregate, indent=2))


if __name__ == '__main__':
    main()
