"""Write local DWI/mask slice PNGs plus HTML; visual review is still required."""
import argparse
import html
import json
from pathlib import Path
import struct
import zlib

import nibabel as nib
import numpy as np


def png(path, rgb):
    height,width,_ = rgb.shape
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
    raw = b''.join(b'\0'+row.tobytes() for row in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--count',type=int,default=8)
    args = parser.parse_args()
    if args.output.exists() or args.count < 1:
        parser.error('Use a new output directory and a positive count')
    manifest = json.loads(args.manifest.read_text())
    root = Path(manifest['data_root']).resolve()
    args.output.mkdir(parents=True)
    cards = []
    for i,study in enumerate(manifest['studies'][:args.count]):
        paths = [(root/study['files'][m]['path']).resolve() for m in ('dwi','mask')]
        if not all(p.is_relative_to(root) for p in paths):
            raise ValueError('Manifest path escapes dataset root')
        image,mask = [nib.as_closest_canonical(nib.load(p)) for p in paths]
        if image.shape != mask.shape or not np.allclose(image.affine,mask.affine,atol=1e-4,rtol=0):
            raise ValueError('DWI and mask grids differ')
        values,labels = image.get_fdata(),mask.get_fdata()
        z = int(np.argmax((labels>0).sum(axis=(0,1)))) if np.any(labels) else values.shape[2]//2
        slice_ = np.rot90(values[:,:,z])
        label = np.rot90(labels[:,:,z]) > 0
        low,high = np.percentile(values[values!=0],[1,99])
        gray = (np.clip((slice_-low)/max(high-low,1e-8),0,1)*255).astype(np.uint8)
        plain = np.repeat(gray[:,:,None],3,axis=2)
        overlay = plain.copy()
        overlay[label] = (.45*overlay[label]+.55*np.array([255,60,60])).astype(np.uint8)
        combined = np.concatenate([plain,overlay],axis=1)
        name = f'study-{i:03d}.png'
        png(args.output/name,combined)
        identity = html.escape(study['subject_id']+'/'+study['study_id'])
        cards.append(f'<section><h2>{identity}</h2><p>Canonical RAS slice index {z}; DWI left, supplied mask overlay right. Display aspect is voxel-based, not physical.</p><img src="{name}" alt="DWI and reference lesion mask" style="max-width:100%;image-rendering:pixelated"></section>')
    title = html.escape(manifest['dataset_id'])
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>NeuroFusion QC</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;background:#f4f7fa;color:#173348}section{background:white;padding:20px;margin:20px 0}</style>'+f'<h1>NeuroFusion image QC: {title}</h1><p>Reference annotations, not model predictions. Selected slices only; full-volume review remains required.</p>'+''.join(cards),encoding='utf-8')
    print(args.output/'index.html')


if __name__ == '__main__':
    main()
