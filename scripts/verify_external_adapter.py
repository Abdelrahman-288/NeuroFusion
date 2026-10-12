"""Reproducible synthetic geometry control; no patient data or model scoring."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from PIL import Image

from neurofusion.data import save_json
from neurofusion.external_adapter import prepare_pair, restore_probabilities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    args.output.mkdir(parents=True)
    x,y,z = np.indices((24,32,16))
    foreground = ((x-12)/10)**2+((y-16)/14)**2+((z-8)/7)**2 < 1
    values = np.where(foreground, 100+x*3+y+z*2, 0).astype(np.float32)
    labels = np.where(((x-10)**2+(y-14)**2+(z-8)**2)<16, 2, 0).astype(np.uint16)
    affine = np.array([[0,0,2,20],[-1,0,0,30],[0,1.5,0,-10],[0,0,0,1.]])
    for name, data in [('image',values),('mask',labels)]:
        volume = nib.Nifti1Image(data,affine)
        volume.header.set_xyzt_units('mm')
        nib.save(volume,args.output/f'{name}.nii.gz')
    images, targets, metadata = prepare_pair(args.output/'image.nii.gz',args.output/'mask.nii.gz',allowed_labels=[0,2])
    np.savez_compressed(args.output/'slices.npz',images=images,numeric_labels=targets)
    save_json(args.output/'geometry.json',metadata)
    # This affine maps increasing native Y to increasing canonical Z.
    signals = np.linspace(0,1,32,dtype=np.float32)
    mock_probabilities = np.broadcast_to(signals[:,None,None],(32,128,128)).copy()
    restored = restore_probabilities(mock_probabilities,metadata)
    expected = np.broadcast_to(signals[None,:,None],values.shape)
    error = float(np.max(np.abs(restored.get_fdata()-expected)))
    if error > 1e-6 or not np.allclose(restored.affine,affine):
        raise AssertionError('Synthetic native-grid roundtrip failed')
    nib.save(restored,args.output/'synthetic-restored.nii.gz')
    mid=len(images)//2
    preview=np.repeat(images[mid,0,:,:,None],3,axis=2)
    preview[targets[mid]>0]=[255,100,50]
    Image.fromarray(preview).save(args.output/'synthetic-preview.png')
    summary={'data':'Synthetic geometry phantom only; no patients or model inference',
        'native_shape':list(values.shape),'canonical_shape':metadata['canonical_shape'],
        'prepared_shape':list(images.shape),'roundtrip_max_absolute_error':error,
        'native_affine_restored':True,'numeric_label_ids':[int(v) for v in np.unique(targets)],
        'label_loss_warnings':metadata['lost_label_slices'],'real_external_volumes':0,
        'evaluation_ready':False,'download_recheck':'Official Aspera package browser navigation timed out on 2026-10-07'}
    save_json(args.output/'summary.json',summary)
    files=[Path(__file__),Path('src/neurofusion/external_adapter.py'),Path('src/neurofusion/pdgm.py')]
    save_json(args.output/'source-hashes.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>External adapter verification</title>'
        '<style>body{font:18px system-ui;max-width:960px;margin:40px auto;padding:20px;background:#101827;color:#e6edf6}pre{white-space:pre-wrap}img{width:256px;image-rendering:pixelated}a{color:#71d6ee}</style>'
        '<h1>External volume adapter verification</h1><p>Synthetic control only. No external MRI acquired or scored.</p>'
        '<img src="synthetic-preview.png" alt="Synthetic phantom with numeric label 2 highlighted">'
        '<pre>'+html.escape(json.dumps(summary,indent=2))+'</pre><p><a href="summary.json">Verification evidence</a></p>',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
