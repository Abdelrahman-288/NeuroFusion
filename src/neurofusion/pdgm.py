"""UCSF-PDGM metadata identity handling and strict volumetric intake checks."""
import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

import nibabel as nib
import numpy as np


def identity(value):
    match = re.fullmatch(r'UCSF-PDGM-(\d{3,4})(?:_FU(\d{3})d)?', value)
    if not match:
        raise ValueError(f'Unexpected UCSF-PDGM identifier: {value}')
    patient = f'UCSF-PDGM-{int(match[1]):04d}'
    days = int(match[2]) if match[2] is not None else None
    return patient, patient + (f'_FU{days:03d}d' if days is not None else ''), days


def read_metadata(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'ID', 'Sex', 'WHO CNS Grade', 'BraTS21 ID'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Required UCSF-PDGM metadata columns missing')
        records, seen = [], set()
        for row in reader:
            patient, exam, days = identity(row['ID'].strip())
            if exam in seen:
                raise ValueError('Duplicate normalized exam identifier')
            seen.add(exam)
            brats = row['BraTS21 ID'].strip()
            if brats and not re.fullmatch(r'BraTS2021_\d{5}', brats):
                raise ValueError('Invalid BraTS mapping')
            records.append({'source_id': row['ID'], 'patient_id': patient, 'exam_id': exam,
                'followup_days': days, 'grade': row['WHO CNS Grade'].strip(),
                'sex': row['Sex'].strip(), 'brats21_id': brats or None})
    if not records:
        raise ValueError('Empty metadata')
    baselines = {r['patient_id']: r for r in records if r['followup_days'] is None}
    for row in records:
        if row['patient_id'] not in baselines:
            raise ValueError('Follow-up lacks baseline patient record')
        if row['sex'] != baselines[row['patient_id']]['sex']:
            raise ValueError('Conflicting sex within a patient group')
    return records


def metadata_summary(records):
    baselines = [r for r in records if r['followup_days'] is None]
    return {'exams': len(records), 'patients': len({r['patient_id'] for r in records}),
        'followup_exams': sum(r['followup_days'] is not None for r in records),
        'exams_with_brats21_mapping': sum(r['brats21_id'] is not None for r in records),
        'patients_with_brats21_mapping': len({r['patient_id'] for r in records if r['brats21_id']}),
        'baseline_grade_counts': dict(Counter(r['grade'] for r in baselines)),
        'mri_volumes_downloaded': 0, 'evaluation_ready': False}


def acquisition_pilot(records, count=20):
    """Stable, label-blind baseline selection for import testing, not a test cohort."""
    if count < 1:
        raise ValueError('Pilot count must be positive')
    baselines = [r for r in records if r['followup_days'] is None]
    key = lambda r: hashlib.sha256(('pdgm-import-pilot-v1:'+r['patient_id']).encode()).hexdigest()
    return sorted(baselines, key=key)[:count]


def audit_volume_pair(image_path, mask_path, *, allowed_labels):
    """Audit aligned native grids; no guessed label meanings, resampling or inference."""
    labels = set(allowed_labels)
    if not labels or any(type(v) is not int or v < 0 for v in labels) or 0 not in labels:
        raise ValueError('Explicit nonnegative integer labels including background 0 required')
    volumes = [nib.load(str(p)) for p in (image_path, mask_path)]
    for volume in volumes:
        if len(volume.shape) != 3 or min(volume.shape) < 2 or np.prod(volume.shape) > 50_000_000:
            raise ValueError('Expected bounded 3D volume')
        if volume.header.get_xyzt_units()[0] != 'mm':
            raise ValueError('Spatial units must explicitly be millimeters')
        affine = volume.affine
        if not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3, :3])) < 1e-8:
            raise ValueError('Invalid affine geometry')
    image, mask = volumes
    if image.shape != mask.shape or not np.allclose(image.affine, mask.affine, atol=1e-4, rtol=0):
        raise ValueError('Image and mask grids differ; do not silently resample')
    values, target = [v.get_fdata(dtype=np.float32) for v in volumes]
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValueError('Nonfinite image or mask values')
    if np.ptp(values) == 0:
        raise ValueError('Constant image')
    if not np.equal(target, np.rint(target)).all() or not set(np.unique(target)).issubset(labels):
        raise ValueError('Unexpected or fractional segmentation labels')
    counts = {str(v): int((target == v).sum()) for v in sorted(labels)}
    return {'shape': list(image.shape), 'axis_codes': list(nib.aff2axcodes(image.affine)),
        'spacing_mm': [float(v) for v in nib.affines.voxel_sizes(image.affine)],
        'label_voxels': counts, 'foreground_voxels': int((target != 0).sum()),
        'geometry_passed': True, 'label_meanings_verified': False, 'evaluation_ready': False,
        'sha256': {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                   for name, path in [('image', image_path), ('mask', mask_path)]}}
