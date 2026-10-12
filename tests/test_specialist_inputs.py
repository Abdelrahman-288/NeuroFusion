import numpy as np
import pytest
from neurofusion.specialist_inputs import *
from neurofusion.eeg import parse_summary,event_scores,patient_group


def test_patient_alias_and_annotation_counts():
    assert patient_group('chb21')==patient_group('chb01')
    s='File Name: chb02_16+.edf\nNumber of Seizures in File: 1\nSeizure Start Time: 4 seconds\nSeizure End Time: 8 seconds\n'
    assert parse_summary(s)[0]['events']==[(4.,8.)]
    with pytest.raises(ValueError):parse_summary(s.replace('File: 1','File: 2'))


def test_event_alarms_do_not_claim_multiple_seizures_and_account_latency():
    r=event_scores([0,1,1,0,1],[(5,7)],20)
    assert r['matched_events']==1 and r['false_alarm_events']==1 and r['latency_seconds']==[3.]
    r=event_scores([1,1,1],[(1,2),(9,10)],12)
    assert r['matched_events']==1


def test_longitudinal_change_requires_registration_and_physical_units():
    a=np.zeros((3,3,3));b=a.copy();b[1,1,1]=1
    affine=np.diag([2,2,2,1])
    r=longitudinal_mask_change(a,b,affine,affine,same_patient=True,registration_verified=True)
    assert r['volume_change_ml']==pytest.approx(.008)
    with pytest.raises(ValueError):longitudinal_mask_change(a,b,affine,affine,same_patient=True,registration_verified=False)
    r=longitudinal_mask_change(b.astype(np.uint8),a.astype(np.uint8),affine,affine,same_patient=True,registration_verified=True)
    assert r['volume_change_ml']==pytest.approx(-.008)
    with pytest.raises(ValueError):longitudinal_mask_change(a,b,affine,affine,same_patient=True,registration_verified=True,spatial_units='meter')


def test_vascular_coordinates_use_declared_lps_geometry():
    affine=np.diag([2.,3.,4.,1.]);affine[:3,3]=[10,20,30]
    assert validate_vascular_targets('CTA',[[12,23,34]],affine,(5,5,5))==[[1.,1.,1.]]
    with pytest.raises(ValueError):validate_vascular_targets('CTA',[[0,0,0]],affine,(5,5,5))


def test_hemorrhage_label_contract(tmp_path):
    p=tmp_path/'labels.csv'
    p.write_text('ID,Label\n'+''.join(f'ID_abc_{c},{int(c in ("any","subdural"))}\n' for c in HEMORRHAGE_LABELS))
    assert rsna_hemorrhage_labels(p)['ID_abc']['any']==1
    p.write_text(p.read_text().replace('ID_abc_any,1','ID_abc_any,0'))
    with pytest.raises(ValueError):rsna_hemorrhage_labels(p)
