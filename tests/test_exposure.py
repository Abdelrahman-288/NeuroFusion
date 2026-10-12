import pytest
from neurofusion.exposure import reference_hits, validate_review


def test_identity_normalizes_padding_and_followups_and_hashes():
    h='a'*64
    assert reference_hits('UCSF-PDGM-255_FU007d '+h, {'UCSF-PDGM-0255'},
                          {h:['UCSF-PDGM-0463']}) == ['UCSF-PDGM-0255','UCSF-PDGM-0463']
    assert reference_hits('UCSF-PDGM-02550', {'UCSF-PDGM-0255'}, {}) == []


def test_pending_does_not_count_and_incomplete_accept_rejected():
    assert not validate_review({'decision':'pending'})
    with pytest.raises(ValueError): validate_review({'decision':'accept'})


def test_review_requires_complete_volume_and_timestamp():
    r=dict(decision='accept',reviewer_name='Test reviewer', reviewer_qualification='Test only',
           reviewed_at='2026-10-09T10:00:00+03:00',notes='Synthetic test',
           image_sha256='a'*64,mask_sha256='b'*64,whole_volume_reviewed=True,
           identity_checked=True,orientation_checked=True,alignment_checked=True)
    assert validate_review(r)
    r['whole_volume_reviewed']=False
    with pytest.raises(ValueError): validate_review(r)
    r['decision']='exclude'
    assert not validate_review(r)
    r['reviewed_at']='2026-10-09'
    with pytest.raises(ValueError): validate_review(r)
