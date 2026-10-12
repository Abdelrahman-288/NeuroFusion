"""Bounded evidence search: references are flags, never proof of model exposure."""
import re
from neurofusion.pdgm import identity

ID_PATTERN = re.compile(r'(?<![A-Za-z0-9])UCSF-PDGM-\d{3,4}(?:_FU\d{3}d)?(?![A-Za-z0-9])')


def reference_hits(text, patients, hashes):
    hits = set()
    for match in ID_PATTERN.finditer(text):
        patient, _, _ = identity(match.group())
        if patient in patients:
            hits.add(patient)
    for token in re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', text.lower()):
        hits.update(hashes.get(token, []))
    return sorted(hits)


def validate_review(record):
    """Validate a human review submission without generating expert judgments."""
    decision = record.get('decision')
    if decision not in ('pending', 'accept', 'exclude', 'needs_followup'):
        raise ValueError('Unknown review decision')
    if decision == 'pending':
        return False
    required = ('reviewer_name', 'reviewer_qualification', 'reviewed_at', 'notes',
                'image_sha256', 'mask_sha256')
    if any(not isinstance(record.get(k), str) or not record[k].strip() for k in required):
        raise ValueError('Reviewer identity, timestamp, notes and source hashes required')
    if any(not re.fullmatch('[0-9a-f]{64}', record[k]) for k in ('image_sha256','mask_sha256')):
        raise ValueError('Invalid source hashes')
    from datetime import datetime
    try:
        reviewed = datetime.fromisoformat(record['reviewed_at'])
        if reviewed.utcoffset() is None:
            raise ValueError('Timezone required')
    except ValueError as error:
        raise ValueError('Timezone-aware review timestamp required') from error
    if decision == 'accept' and (record.get('whole_volume_reviewed') is not True
            or any(record.get(k) is not True for k in
                   ('identity_checked', 'orientation_checked', 'alignment_checked'))):
        raise ValueError('Acceptance requires complete whole-volume review checks')
    return decision == 'accept'
