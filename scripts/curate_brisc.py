"""Conservative image-group partitions and mask encoding audit; no patient independence claim."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.fft import dctn
from neurofusion.data import save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Fresh output required')
    rows=[r for r in json.loads((args.audit/'manifest.json').read_text())['files'] if r['task']=='classification']
    args.output.mkdir(parents=True)
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    def union(i,j):
        a,b=find(i),find(j)
        if a!=b: parent[b]=a
    hashes=[]; exact={}
    for i,row in enumerate(rows):
        path=args.root/row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Image changed since audit')
        with Image.open(path) as image:
            small=np.asarray(image.convert('L').resize((32,32)),dtype=np.float32)
        frequencies=dctn(small,type=2,norm='ortho')[:8,:8].ravel()[1:]
        code=int(''.join('1' if bit else '0' for bit in frequencies>np.median(frequencies)),2)
        hashes.append(code)
        if row['pixel_sha256'] in exact: union(i,exact[row['pixel_sha256']])
        else: exact[row['pixel_sha256']]=i
        if (i+1)%1000==0: print(f'Fingerprint {i+1}/{len(rows)}',flush=True)
    near=[]
    for i,ha in enumerate(hashes):
        for j in range(i):
            distance=(ha^hashes[j]).bit_count()
            if distance<=4:
                union(i,j)
                near.append({'a':rows[i]['path'],'b':rows[j]['path'],'distance':distance})
    groups=defaultdict(list)
    for i,row in enumerate(rows): groups[find(i)].append(row)
    assignments=[]; group_info=[]
    for members in groups.values():
        gid=hashlib.sha256('\n'.join(sorted(r['path'] for r in members)).encode()).hexdigest()
        source_test=any(r['source_split']=='test' for r in members)
        conflict=len({r['label'] for r in members})>1
        # Hash assignment is reproducible, label-independent and keeps each group together.
        partition='validation' if int(hashlib.sha256(('42:'+gid).encode()).hexdigest()[:8],16)%5==0 else 'train'
        for row in members:
            target='quarantine' if conflict else ('test' if row['source_split']=='test' else 'quarantine') if source_test else partition
            assignments.append({**row,'group_id':gid,'partition':target,
                'reason':'label_conflict' if conflict else 'possible_test_overlap' if source_test and row['source_split']=='train' else 'group_partition'})
        group_info.append({'group_id':gid,'members':len(members),'touches_source_test':source_test,'label_conflict':conflict})
    publisher=json.loads((args.root/'manifest.json').read_text())
    masks=[]; histogram=np.zeros(256,dtype=np.int64)
    for row in publisher:
        if not row['is_mask']: continue
        path=args.root/row['relative_path'].replace('\\','/')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']: raise ValueError('Mask publisher checksum mismatch')
        with Image.open(path) as image:
            if image.mode!='L': raise ValueError('Unexpected mask encoding')
            array=np.asarray(image)
        if array.shape!=(row['height'],row['width']): raise ValueError('Mask dimensions differ')
        counts=np.bincount(array.ravel(),minlength=256)
        histogram+=counts
        masks.append({'path':row['relative_path'].replace('\\','/'),'sha256':row['sha256'],
                      'intermediate_pixels':int(counts[1:255].sum()),'foreground_at_128':int(counts[128:].sum())})
    active=defaultdict(set)
    for row in assignments:
        if row['partition']!='quarantine': active[row['group_id']].add(row['partition'])
    if any(len(v)>1 for v in active.values()): raise ValueError('Image group crosses partitions')
    summary={'classification_images':len(rows),'partitions':dict(Counter(r['partition'] for r in assignments)),
        'class_counts':dict(Counter(r['partition']+'/'+r['label'] for r in assignments)),
        'groups':len(groups),'similarity_edges':len(near),'label_conflict_groups':sum(g['label_conflict'] for g in group_info),
        'no_active_group_overlap':True,'masks_checksum_verified':len(masks),'masks_with_intermediate_values':sum(r['intermediate_pixels']>0 for r in masks),
        'mask_histogram':histogram.tolist(),'patient_independence':False,
        'classification_ready_for_exploratory_baseline':True,'segmentation_ready':False,
        'limitations':'63-bit DCT distance <=4 plus exact hashes form conservative groups; similarity does not prove patient identity. Label-conflict groups and training images connected to source test are quarantined. Threshold-128 mask counts are descriptive, not approved segmentation targets.'}
    save_json(args.output/'splits.json',{'seed':42,'frozen':True,'scope':'image-similarity groups, NOT patient-level',
        'source_manifest_sha256':hashlib.sha256((args.audit/'manifest.json').read_bytes()).hexdigest(),'assignments':assignments})
    save_json(args.output/'groups.json',group_info)
    save_json(args.output/'similarity-edges.json',near)
    save_json(args.output/'mask-audit.json',masks)
    save_json(args.output/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='mask_histogram'},indent=2))


if __name__=='__main__': main()
