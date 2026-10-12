"""Separate diagnostic abstention from a checkpoint-bound development screen."""
import numpy as np

CLASSIFIER_SHA='41bce20f491d345adeac31341b0f6a4ccf8908383bcf76e583962a5989180235'
CUTOFF=0.3612370491027832


def uncertainty_decision(task,models,scores=None):
    result=dict(policy_version='research-abstention-v1',decision='abstain',
        reliable_prediction_available=False,calibration_applied=False,
        reason='Independent calibration and reliability have not been established for this input.',
        raw_outputs_available_for_research=True,
        segmentation=dict(decision='not_qualified',reason='No qualified calibration/abstention policy for the active segmenter'))
    if task=='tumor-image' and models.get('tumor_classifier')==CLASSIFIER_SHA and scores is not None:
        p=np.asarray(scores,dtype=float)
        if p.shape!=(4,) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not np.isclose(p.sum(),1,atol=1e-5):
            raise ValueError('Four normalized finite class scores required')
        uncertainty=float(1-p.max())
        result['classification_development_screen']=dict(
            decision='withhold' if uncertainty>CUTOFF else 'within_development_cutoff',
            uncertainty=uncertainty,cutoff=CUTOFF,calibration='identity; recalibration rejected',
            checkpoint_sha256=CLASSIFIER_SHA,
            evidence='experiments/tumor-classifier-uncertainty-003/summary.json',
            independent_reliability=False,
            note='Passing this development cutoff does not override overall abstention or imply a correct prediction.')
    else:
        result['classification_development_screen']=dict(decision='unavailable',reason='Unsupported task or changed checkpoint')
    return result
