"""Controlled perturbations of the classifier's 128x128 normalized input grid."""
import numpy as np
from scipy.ndimage import gaussian_filter
from neurofusion.tumor import classification_metrics

CONDITIONS = ('clean','brightness_080','brightness_120','contrast_080','noise_003','blur_100')


def perturb(images, condition, seed=20261006):
    values = np.asarray(images, dtype=np.float32)
    if values.ndim != 4 or values.shape[1] != 1 or not np.isfinite(values).all() or values.min()<0 or values.max()>1:
        raise ValueError('Expected finite normalized NCHW grayscale images')
    if condition not in CONDITIONS:
        raise ValueError('Unknown perturbation')
    if condition == 'clean': output = values.copy()
    elif condition == 'brightness_080': output = values * .8
    elif condition == 'brightness_120': output = values * 1.2
    elif condition == 'contrast_080': output = (values-.5)*.8+.5
    elif condition == 'noise_003': output = values + np.random.default_rng(seed).normal(0,.03,values.shape).astype(np.float32)
    else: output = gaussian_filter(values, sigma=(0,0,1,1), mode='reflect')
    return np.clip(output,0,1).astype(np.float32)


def summarize(labels, probabilities, clean, groups):
    result = classification_metrics(labels, probabilities)
    clean = np.asarray(clean); probabilities = np.asarray(probabilities); labels = np.asarray(labels)
    # Also validates the clean reference rather than silently comparing malformed scores.
    classification_metrics(labels, clean)
    if len(groups)!=len(labels): raise ValueError('Group count mismatch')
    correct = probabilities.argmax(1)==labels
    original_correct = clean.argmax(1)==labels
    result.update(flip_rate=float((probabilities.argmax(1)!=clean.argmax(1)).mean()),
                  mean_absolute_score_shift=float(np.abs(probabilities-clean).mean()),
                  correct_to_wrong=int((original_correct & ~correct).sum()),
                  wrong_to_correct=int((~original_correct & correct).sum()),
                  equal_group_accuracy=float(np.mean([correct[np.asarray(groups)==g].mean() for g in sorted(set(groups))])))
    return result
