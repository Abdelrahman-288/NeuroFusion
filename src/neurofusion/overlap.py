"""Label-free 2D dataset overlap screening; never certifies patient independence."""
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.fft import dctn


def fingerprint(path):
    path = Path(path)
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Only single-frame 2D images are supported')
        rgb = np.asarray(image.convert('RGB'))
        small = np.asarray(image.convert('L').resize((32, 32)), dtype=np.float32)
    frequencies = dctn(small, type=2, norm='ortho')[:8, :8].ravel()[1:]
    bits = frequencies > np.median(frequencies)
    return {
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'pixel_sha256': hashlib.sha256(str(rgb.shape).encode() + rgb.tobytes()).hexdigest(),
        'phash': int(''.join('1' if bit else '0' for bit in bits), 2),
        'constant': bool(rgb.min() == rgb.max()),
    }


def index_images(root, rows):
    """Resolve a declared image manifest, rejecting escapes and changed checksums."""
    root = Path(root).resolve()
    if not rows:
        raise ValueError('Image manifest is empty')
    result, seen = [], set()
    for row in rows:
        rel = row['path']
        path = (root / rel).resolve()
        if Path(rel).is_absolute() or not path.is_relative_to(root) or path in seen:
            raise ValueError('Unsafe or duplicate image path')
        seen.add(path)
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            raise ValueError('Only PNG/JPEG inputs are supported; volumes need a separate audit')
        patient = row.get('patient_id')
        if patient is not None and (not isinstance(patient, str) or not patient.strip()):
            raise ValueError('patient_id must be a nonempty source identifier or null')
        info = fingerprint(path)
        if row.get('sha256') and info['sha256'] != row['sha256']:
            raise ValueError(f'File checksum mismatch: {rel}')
        result.append({'path': rel, 'patient_id': patient, **info})
    return result


def screen_overlap(reference, candidates, threshold=4):
    if not reference or not candidates:
        raise ValueError('Both cohorts must be nonempty')
    if not isinstance(threshold, int) or not 0 <= threshold <= 63:
        raise ValueError('Hamming threshold must be between 0 and 63')
    matches = []
    exact, near = set(), set()
    for candidate in candidates:
        for ref in reference:
            distance = (candidate['phash'] ^ ref['phash']).bit_count()
            kind = ('exact_file' if candidate['sha256'] == ref['sha256'] else
                    'exact_pixels' if candidate['pixel_sha256'] == ref['pixel_sha256'] else
                    'similarity_candidate' if distance <= threshold else None)
            if kind:
                matches.append({'candidate': candidate['path'], 'reference': ref['path'],
                                'kind': kind, 'hamming_distance': distance})
                (near if kind == 'similarity_candidate' else exact).add(candidate['path'])
    flagged = exact | near
    patients = {r['patient_id'] for r in candidates if r['path'] in flagged and r['patient_id']}
    dispositions = []
    for row in candidates:
        reason = ('exact_overlap' if row['path'] in exact else
                  'similarity_review' if row['path'] in near else
                  'flagged_patient' if row['patient_id'] in patients else
                  'constant_image' if row['constant'] else 'no_match_found')
        dispositions.append({'path': row['path'], 'patient_id': row['patient_id'], 'reason': reason})
    return {
        'method': 'RGB decoded SHA256 and file SHA256; 63-bit DCT hash',
        'hamming_threshold': threshold,
        'reference_images': len(reference), 'candidate_images': len(candidates),
        'exact_overlap_images': len(exact), 'similarity_only_images': len(near - exact),
        'flagged_patient_count': len(patients),
        'patient_propagated_images': sum(r['reason'] == 'flagged_patient' for r in dispositions),
        'missing_candidate_patient_ids': sum(not r['patient_id'] for r in candidates),
        'evaluation_ready': False,
        'remaining_gate': 'Manual source-lineage, patient identity, task/label, license and protocol review required even with zero matches.',
        'limitations': 'Near matches are review candidates, not proof of duplication. Crops, rotations, adjacent slices and shared patients can escape detection. No model inference is performed.',
        'matches': matches, 'dispositions': dispositions,
    }
