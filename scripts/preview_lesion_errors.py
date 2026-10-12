"""Render the largest completely missed and non-overlapping predicted components."""
import argparse
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from scipy import ndimage
from neurofusion.cohort import StudyStore, digest
from neurofusion.data import save_json
from preview_studies import png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['analysis', 'manifest', 'splits', 'cache']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((args.analysis / 'protocol.json').read_text())
    report = json.loads((args.analysis / 'summary.json').read_text())
    if digest(args.manifest) != protocol['manifest_sha256'] or digest(args.splits) != protocol['splits_sha256']:
        raise ValueError('Analysis dataset binding mismatch')
    output = args.analysis / 'error-gallery'
    if output.exists() and any(output.iterdir()):
        raise ValueError('Gallery already contains files')
    output.mkdir(exist_ok=True)
    store = StudyStore(args.manifest, args.splits, args.cache)
    studies = {s['subject_id']: s for s in store.studies('validation')}
    cards, evidence = [], []
    for category, examples in report['examples'].items():
        for example in examples:
            subject = example['subject']
            image, reference, meta = store.load(studies[subject])
            path = Path(protocol['run']) / 'predictions' / f'{subject}-probability.nii.gz'
            detail = json.loads((args.analysis / 'cases' / f'{subject}.json').read_text())
            if digest(path) != detail['prediction_sha256']:
                raise ValueError('Prediction changed since analysis')
            prediction_image = nib.as_closest_canonical(nib.load(path))
            if prediction_image.shape != reference.shape or not np.allclose(prediction_image.affine, meta['canonical_affine'], atol=1e-4, rtol=0):
                raise ValueError('Prediction grid mismatch')
            prediction = prediction_image.get_fdata(dtype=np.float32) >= .5
            missed = category == 'largest_completely_missed'
            labels, _ = ndimage.label(reference if missed else prediction, ndimage.generate_binary_structure(3, 3))
            component = labels == example['component']
            if int(component.sum()) != example['voxels']:
                raise ValueError('Component identity mismatch')
            z = int(np.argmax(component.sum(axis=(0, 1))))
            low, high = np.percentile(image[image != 0], [1, 99])
            gray = (np.clip((np.rot90(image[:, :, z]) - low) / max(high - low, 1e-8), 0, 1) * 255).astype(np.uint8)
            plain = np.repeat(gray[:, :, None], 3, axis=2)
            panels = [plain]
            for mask in (reference > 0, prediction, component):
                overlay = plain.copy()
                plane = np.rot90(mask[:, :, z])
                overlay[plane] = (.45 * overlay[plane] + .55 * np.array([255, 60, 60])).astype(np.uint8)
                panels.append(overlay)
            name = f'{category}-{subject}-{example["component"]}.png'
            png(output / name, np.concatenate(panels, axis=1))
            title = 'Completely missed reference component' if missed else 'Predicted component with no reference overlap'
            cards.append(f'<section><h2>{title}</h2><p>{html.escape(subject)} · component {example["component"]} · {example["volume_ml"]:.3f} mL · slice {z}</p><p>DWI | full reference | full prediction | selected component</p><img src="{name}" alt="Four panels comparing DWI, reference, prediction and selected error"></section>')
            evidence.append({**example, 'category': category, 'slice': z, 'image': name})
    save_json(output / 'examples.json', evidence)
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>NeuroFusion error gallery</title><style>body{font:17px system-ui;max-width:1250px;margin:30px auto;padding:20px;color:#173348}section{border-top:1px solid #bbb;margin-top:30px}img{width:100%;image-rendering:pixelated}</style><h1>Validation error gallery</h1><p>Three largest completely missed reference components and three largest predictions with zero reference overlap. Selection uses 26-connectivity and threshold 0.5. Each slice maximizes the selected component area; these examples are not representative sampling or clinical interpretation. Display aspect is voxel-based.</p><a href="../index.html">All-study analysis</a>' + ''.join(cards), encoding='utf-8')
    print(output / 'index.html')


if __name__ == '__main__':
    main()
