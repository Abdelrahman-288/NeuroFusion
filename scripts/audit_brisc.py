"""Audit 2D BRISC images, paired masks and exact decoded-content duplication."""
import argparse
from collections import Counter,defaultdict
import hashlib
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.fft import dctn
from neurofusion.data import save_json


def inspect_image(path,mask=False):
    with Image.open(path) as image:
        image.load()
        values=np.asarray(image.convert('L') if mask else image.convert('RGB'))
    if min(values.shape[:2])<2:
        raise ValueError('Image too small')
    unique=np.unique(values) if mask else None
    if mask and not set(unique.tolist()).issubset({0,1,255}):
        raise ValueError('Mask has non-binary intensities')
    return {'shape':list(values.shape),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'pixel_sha256':hashlib.sha256(str(values.shape).encode()+values.tobytes()).hexdigest(),
            'constant':bool(values.min()==values.max()),
            **({'mask_values':unique.tolist(),'foreground_pixels':int((values>0).sum())} if mask else {})}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use fresh audit output')
    args.output.mkdir(parents=True)
    publisher={}
    for name in ['manifest.json','manifest.csv']:
        expected=(args.root/(name+'.sha256')).read_text().split()[0]
        actual=hashlib.sha256((args.root/name).read_bytes()).hexdigest()
        if actual!=expected:
            raise ValueError('Publisher manifest checksum mismatch')
    for item in json.loads((args.root/'manifest.json').read_text(encoding='utf-8')):
        rel=item['relative_path'].replace('\\','/')
        path=(args.root/rel).resolve()
        if not path.is_relative_to(args.root.resolve()) or rel in publisher:
            raise ValueError('Unsafe or duplicate manifest entry')
        publisher[rel]=item
    rows=[]; errors=[]; counts=Counter(); pixels=defaultdict(list); masks={}; samples={}
    perceptual=[]
    for path in sorted(args.root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.jpg','.jpeg','.png'):
            continue
        rel=path.relative_to(args.root).as_posix()
        parts=path.parts
        task='classification' if 'classification_task' in parts else 'segmentation' if 'segmentation_task' in parts else 'other'
        split='train' if 'train' in parts else 'test' if 'test' in parts else 'unknown'
        is_mask='masks' in parts
        try:
            info=inspect_image(path,is_mask)
            source=publisher.get(rel)
            if source is None or info['sha256']!=source['sha256'] or path.stat().st_size!=source['file_size_bytes']:
                raise ValueError('Publisher file checksum/size mismatch or unlisted file')
            if info['shape'][:2]!=[source['height'],source['width']]:
                raise ValueError('Publisher dimensions mismatch')
            row={'path':rel,'task':task,'source_split':split,'is_mask':is_mask,**info}
            if task=='classification':
                row['label']=path.parent.name
                samples[(split,path.stem)]=row
                counts[f'{split}/{path.parent.name}']+=1
                with Image.open(path) as image:
                    small=np.asarray(image.convert('L').resize((32,32)),dtype=np.float32)
                frequencies=dctn(small,type=2,norm='ortho')[:8,:8].ravel()[1:]
                bits=frequencies>np.median(frequencies)
                code=int(''.join('1' if bit else '0' for bit in bits),2)
                perceptual.append((row,code))
            elif is_mask:
                masks[(split,path.stem)]=row
            if not is_mask:
                pixels[info['pixel_sha256']].append(row)
            rows.append(row)
        except Exception as error:
            errors.append({'path':rel,'error':str(error)})
    pairing=[]
    missing=set(publisher)-{r['path'] for r in rows}-{r['path'] for r in errors}
    errors.extend({'path':p,'error':'Publisher file missing'} for p in sorted(missing))
    for row in rows:
        if row['task']!='segmentation' or row['is_mask']:
            continue
        key=(row['source_split'],Path(row['path']).stem)
        mask=masks.pop(key,None)
        classification=samples.get(key)
        if mask is None or row['shape'][:2]!=mask['shape'][:2]:
            pairing.append({'path':row['path'],'error':'Missing or mismatched mask'})
        if classification is None or row['pixel_sha256']!=classification['pixel_sha256']:
            pairing.append({'path':row['path'],'error':'Classification copy missing or differs'})
    pairing.extend({'path':row['path'],'error':'Orphan mask'} for row in masks.values())
    duplicates=[{'pixel_sha256':key,'paths':[r['path'] for r in group],
                 'cross_source_split':len({r['source_split'] for r in group})>1,
                 'classification_copies':sum(r['task']=='classification' for r in group)}
                for key,group in pixels.items() if len(group)>1]
    classification_dupes=[g for g in duplicates if g['classification_copies']>1]
    near=[]
    train=[item for item in perceptual if item[0]['source_split']=='train']
    test=[item for item in perceptual if item[0]['source_split']=='test']
    for a,ha in train:
        for b,hb in test:
            distance=(ha^hb).bit_count()
            if distance<=4 and a['pixel_sha256']!=b['pixel_sha256']:
                near.append({'train':a['path'],'test':b['path'],'hamming_distance':distance,
                             'same_label':a['label']==b['label']})
    near.sort(key=lambda row:row['hamming_distance'])
    save_json(args.output/'near-duplicate-candidates.json',{'method':'63-bit low-frequency DCT hash; cross-source-split Hamming distance <=4; excludes exact decoded duplicates',
        'warning':'Similarity candidates only, not proof of same patient or duplication. Review required.', 'pairs':near})
    summary={'image_and_mask_files':len(rows),'decode_errors':len(errors),'pairing_errors':len(pairing),
        'publisher_manifest_checksums_passed':True,'publisher_file_records':len(publisher),
        'classification_images':sum(r['task']=='classification' for r in rows),
        'segmentation_images':sum(r['task']=='segmentation' and not r['is_mask'] for r in rows),
        'segmentation_masks':sum(r['is_mask'] for r in rows),'classification_counts':dict(counts),
        'duplicate_groups_including_task_copies':len(duplicates),'classification_duplicate_groups':len(classification_dupes),
        'cross_source_split_duplicate_groups':sum(g['cross_source_split'] for g in duplicates),
        'cross_source_split_near_duplicate_candidates':len(near),
        'constant_images':sum(r['constant'] and not r['is_mask'] for r in rows),
        'empty_masks':sum(r.get('foreground_pixels',1)==0 for r in rows),
        'patient_independence':'Not established; filenames are image IDs, not patient IDs.',
        'training_ready':False,'remaining_gate':'Near-duplicate review and explicit image-level split policy; no patient-independent claim.',
        'data_integrity_passed':not errors and not pairing,'root':str(args.root.resolve())}
    save_json(args.output/'manifest.json',{'dataset':'brisc-v6','root':str(args.root.resolve()),'files':rows})
    save_json(args.output/'summary.json',summary)
    save_json(args.output/'issues.json',{'decode':errors,'pairing':pairing,'duplicates':duplicates})
    cards=[]
    for label in sorted({r.get('label') for r in rows if r.get('label')}):
        row=next(r for r in rows if r.get('label')==label and r['source_split']=='train')
        source=args.root/row['path']
        with Image.open(source) as image:
            image.convert('RGB').save(args.output/f'{label}.png')
        cards.append(f'<div><h3>{html.escape(label)}</h3><img src="{label}.png" width="240"></div>')
    table=''.join(f'<tr><td>{html.escape(k)}</td><td>{v}</td></tr>' for k,v in counts.items())
    (args.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>BRISC dataset audit</title><style>body{font:17px system-ui;max-width:1100px;margin:30px auto;padding:20px}td{padding:8px}img{max-width:100%}.examples{display:flex;flex-wrap:wrap;gap:20px}</style><h1>BRISC v6 · dataset audit</h1><p>2D image classification and tumor-mask data. No tumor model trained yet. Patient independence is unverified; no_tumor does not mean healthy.</p><table>'+table+'</table><p>'+html.escape(json.dumps({k:v for k,v in summary.items() if k not in ['classification_counts','root']}))+'</p><h2>Selected training images</h2><div class="examples">'+''.join(cards)+'</div><p><a href="summary.json">Summary</a> · <a href="issues.json">Duplicate and pairing evidence</a></p>',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
