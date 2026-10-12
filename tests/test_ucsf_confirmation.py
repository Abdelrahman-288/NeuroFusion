import pytest
from neurofusion.ucsf_confirmation import confirm_pairs


def run(dice):
    return {'final_epoch':{'cases':[{'patient_id':'p','metrics':{'dice':dice,'iou':dice/(2-dice),'fp':1,'voxel_ml':.001}}]}}


def test_confirmation_cannot_hide_failed_seed_with_average():
    pairs={42:(run(.5),run(.9)),43:(run(.5),run(.9)),44:(run(.5),run(.49))}
    assert not confirm_pairs(pairs)['all_seeds_passed']
    pairs[44]=(run(.5),run(.6))
    assert confirm_pairs(pairs)['all_seeds_passed']
    assert not confirm_pairs(pairs)['model_promoted']


def test_confirmation_requires_every_predeclared_seed():
    with pytest.raises(ValueError):confirm_pairs({42:(run(.5),run(.6))})
