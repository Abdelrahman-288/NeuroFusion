"""Snapshot provisional intake without inference, resampling or cohort promotion."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil

import nibabel as nib
import numpy as np

from neurofusion.data import save_json
from neurofusion.external_import import digest
from neurofusion.pdgm import audit_volume_pair, identity, read_metadata


def pixel_digest(path):
    volume = nib.as_closest_canonical(nib.load(str(path)))
    values = np.asarray(volume.get_fdata(dtype=np.float32), dtype='<f4')
    h = hashlib.sha256(str(values.shape).encode())
    h.update(values.tobytes(order='C'))
    return h.hexdigest()


def run(root, downloads, output):
    root, downloads, output = map(lambda p: Path(p).resolve(), (root, downloads, output))
    if output.exists():
        raise ValueError('Use a fresh output directory; previous evidence is immutable')
    sources = {'queue': root/'experiments/ucsf-qualification-001/acquisition-queue.json',
               'development': root/'data/ucsf-import-manifest.json',
               'metadata': root/'data/downloads/ucsf-pdgm-v5-metadata/metadata_v5.csv'}
    queue = json.loads(sources['queue'].read_text(encoding='utf-8-sig'))
    development = json.loads(sources['development'].read_text(encoding='utf-8-sig'))['records']
    metadata = read_metadata(sources['metadata'])
    mapped = {r['patient_id'] for r in metadata if r['brats21_id']}
    known = {r['exam_id']: r for r in metadata}
    dev_ids = {r['patient_id'] for r in development}
    seen_ids = set()
    # Validate the complete queue before copying or creating output.
    for row in queue['records']:
        patient, exam, followup = identity(row['exam_id'])
        expected = [exam+'_T1c.nii.gz', exam+'_tumor_segmentation.nii.gz']
        if (patient != row['patient_id'] or followup is not None or patient in seen_ids
                or patient in dev_ids or patient in mapped or exam not in known
                or row['files'] != expected):
            raise ValueError('Queue identity, filenames, or known-overlap check failed')
        seen_ids.add(patient)
    fingerprints = {}
    for row in development:
        path = root/'data/raw/ucsf-pdgm-v5'/row['image']['path']
        if digest(path) != row['image']['sha256']:
            raise ValueError('Development reference checksum changed')
        fingerprints[pixel_digest(path)] = row['exam_id']
    output.mkdir(parents=True)
    save_json(output/'queue.json', queue)
    results = []
    for row in queue['records']:
        record = {'exam_id': row['exam_id'], 'patient_id': row['patient_id'],
                  'status': 'awaiting_files', 'files': []}
        results.append(record)
        matches = [list(downloads.rglob(name)) for name in row['files']]
        if any(len(paths) > 1 for paths in matches):
            record.update(status='failed', error='Ambiguous duplicate filenames in download directory')
            continue
        if any(not paths for paths in matches):
            record['missing_files'] = [n for n, paths in zip(row['files'], matches) if not paths]
            continue
        pair = [paths[0] for paths in matches]
        try:
            before = [digest(p) for p in pair]
            audit = audit_volume_pair(*pair, allowed_labels=[0, 1, 2, 4])
            fingerprint = pixel_digest(pair[0])
            if fingerprint in fingerprints:
                raise ValueError('Exact canonical voxel duplicate of '+fingerprints[fingerprint])
            if before != [digest(p) for p in pair]:
                raise ValueError('Source changed while auditing')
            target = output/'raw'/row['exam_id']
            target.mkdir(parents=True)
            for source, sha in zip(pair, before):
                destination = target/source.name
                shutil.copyfile(source, destination)
                if digest(destination) != sha:
                    raise ValueError('Copied file checksum mismatch')
                record['files'].append({'path': destination.relative_to(output).as_posix(),
                                        'source_path': str(source), 'bytes': destination.stat().st_size,
                                        'sha256': sha})
            fingerprints[fingerprint] = row['exam_id']
            # Do not expose target burden summaries as a selection aid in this intake report.
            audit.pop('label_voxels', None)
            audit.pop('foreground_voxels', None)
            record.update(status='integrity_verified', audit=audit,
                          canonical_voxel_sha256=fingerprint)
        except (ValueError, OSError, nib.filebasedimages.ImageFileError) as error:
            record.update(status='failed', error=str(error))
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'planned_pairs': len(results),
               'verified_pairs': sum(r['status']=='integrity_verified' for r in results),
               'failed_pairs': sum(r['status']=='failed' for r in results),
               'awaiting_pairs': sum(r['status']=='awaiting_files' for r in results),
               'independence_verified': False, 'cohort_frozen': False,
               'expert_reviewed': False, 'model_inference_performed': False,
               'results': results,
               'limitations': 'Exact canonical voxel and known identity/mapping checks only; '
                   'near-duplicate, cross-dataset and expert alignment review remain. '
                   'Local hashes are not publisher checksums. No clinical label semantics certified.'}
    save_json(output/'summary.json', summary)
    save_json(output/'provenance.json', {
        'source': 'https://www.cancerimagingarchive.net/collection/ucsf-pdgm/',
        'version': 5, 'package_id': '1065', 'license': 'CC BY 4.0',
        'citation': 'Calabrese et al. (2022), UCSF-PDGM Version 5, DOI 10.7937/tcia.bdgf-8v37',
        'transfer_method': 'Official Aspera browser selected-file downloads with installed IBM client',
        'input_sha256': {k: digest(v) for k,v in sources.items()},
        'script_sha256': digest(Path(__file__)),
        'audit_source_sha256': digest(root/'src/neurofusion/pdgm.py')})
    shutil.copyfile(__file__, output/'build-script.py')
    rows = ''.join('<tr><td>'+html.escape(r['exam_id'])+'</td><td>'+r['status']+'</td></tr>' for r in results)
    output.joinpath('index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>UCSF acquisition audit</title>'
        '<style>body{max-width:900px;margin:40px auto;padding:20px;background:#101e2c;color:#eee;font:17px system-ui}'
        'progress{width:100%;height:28px}td,th{padding:10px;text-align:left;border-bottom:1px solid #567}'
        'a{color:#80ded0}</style><h1>Provisional UCSF acquisition audit</h1>'
        f'<h2>{summary["verified_pairs"]}/{len(results)} pairs verified</h2>'
        f'<progress max="{len(results)}" value="{summary["verified_pairs"]}"></progress>'
        '<p>Acquisition integrity only. This is not model accuracy, overall project completion, '
        'independent-cohort certification, or clinical readiness.</p><p>'+html.escape(summary['limitations'])+'</p>'
        '<p>No training or inference performed. The cohort remains provisional.</p>'
        '<table><tr><th>Exam</th><th>Intake status</th></tr>'+rows+'</table>'
        '<p><a href="summary.json">Audit details</a> · <a href="provenance.json">Provenance</a></p></html>', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--downloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.downloads, args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='results'}, indent=2))
    if result['failed_pairs']:
        raise SystemExit(1)
