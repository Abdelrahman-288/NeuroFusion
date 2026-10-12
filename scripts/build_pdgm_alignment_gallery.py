"""Create a static, original-grid review gallery; never certify alignment."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import nibabel as nib
import numpy as np
from PIL import Image
from neurofusion.pdgm import audit_volume_pair


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    manifest = json.loads(args.manifest.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    sections, cases = [], []
    for number, record in enumerate(manifest['records'], 1):
        paths = []
        for role in ('image', 'mask'):
            path = (root/record[role]['path']).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Source escapes root')
            if hashlib.sha256(path.read_bytes()).hexdigest() != record[role]['sha256']:
                raise ValueError('Source checksum changed')
            paths.append(path)
        audit_volume_pair(*paths, allowed_labels=record['allowed_labels'])
        image, mask = [nib.as_closest_canonical(nib.load(path)) for path in paths]
        # Axis annotations below are only valid for axis-aligned RAS grids.
        if not np.allclose(image.affine[:3,:3], np.diag(np.diag(image.affine[:3,:3])), atol=1e-4):
            raise ValueError('Oblique grid needs a separate review rendering policy')
        data = image.get_fdata(dtype=np.float32)
        labels = mask.get_fdata(dtype=np.float32)
        low, high = np.percentile(data[data != 0], [1,99])
        if high <= low:
            raise ValueError('Degenerate display window')
        gray = np.rint(np.where(data != 0, np.clip((data-low)/(high-low),0,1),0)*255).astype(np.uint8)
        spacing = nib.affines.voxel_sizes(image.affine)
        directory = args.output/f'case-{number:02d}'; directory.mkdir()
        cards, planes = [], []
        for axis, name, directions in [(0,'Sagittal','left P / right A; top S'),
                                       (1,'Coronal','left L / right R; top S'),
                                       (2,'Axial','left L / right R; top A')]:
            remaining = [i for i in range(3) if i != axis]
            for fraction in (.25,.5,.75):
                index = round((data.shape[axis]-1)*fraction)
                plane = np.rot90(np.take(gray,index,axis=axis))
                lab = np.rot90(np.take(labels,index,axis=axis))
                base = np.repeat(plane[:,:,None],3,axis=2)
                overlay = np.zeros((*plane.shape,4),dtype=np.uint8)
                for label,color in [(1,(255,90,90)),(2,(90,230,140)),(4,(80,155,255))]:
                    overlay[lab==label] = (*color,125)
                stem = f'{axis}-{index}'
                Image.fromarray(base).save(directory/f'{stem}.png')
                Image.fromarray(overlay).save(directory/f'{stem}-mask.png')
                # Original pixels are stored; CSS preserves physical aspect ratio.
                ratio = plane.shape[1]*spacing[remaining[0]]/(plane.shape[0]*spacing[remaining[1]])
                base_url=f'{directory.name}/{stem}.png'; mask_url=f'{directory.name}/{stem}-mask.png'
                cards.append(f'<figure><div class="slice" style="aspect-ratio:{ratio}"><img src="{base_url}" alt="{name} MRI"><img class="mask" src="{mask_url}" alt="Numeric mask overlay"></div><figcaption>{name} · canonical index {index}<br>{directions}</figcaption></figure>')
                planes.append({'axis':axis,'canonical_index':index,'fraction':fraction,
                               'base':base_url,'overlay':mask_url,'display_directions':directions})
        exam=html.escape(record['exam_id'])
        sections.append(f'<section id="case-{number:02d}"><h2>{exam}</h2><p>Alignment review: pending · numeric labels only</p><div class="grid">'+''.join(cards)+'</div></section>')
        cases.append({'exam_id':record['exam_id'],'alignment_review':'pending','source_sha256':{k:record[k]['sha256'] for k in ('image','mask')},'canonical_affine':image.affine.tolist(),'window_p1_p99':[float(low),float(high)],'planes':planes})
        print(f'{number}/{len(manifest["records"])} rendered',flush=True)
    navigation=''.join(f'<a href="#case-{i:02d}">{html.escape(c["exam_id"])}</a> ' for i,c in enumerate(cases,1))
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>NeuroFusion alignment review</title>
<style>body{font:16px system-ui;background:#101b2b;color:#ecf3fb;margin:24px auto;padding:16px;max-width:1200px}a{color:#81cbff}nav{line-height:2}header{position:sticky;top:0;background:#101b2b;z-index:2;padding:12px;border-bottom:1px solid #445}button{padding:10px;font-size:16px}section{scroll-margin-top:130px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}.slice{position:relative;background:black}.slice img{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated}figcaption{padding:8px}body.hide .mask{display:none}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<header><h1>Original-grid alignment review</h1><button id="toggle" aria-pressed="true">Hide mask overlays</button> <span>1 red · 2 green · 4 blue</span></header>
<p>Technical review aid only. All exams remain pending. Label meanings are candidates, not version-confirmed. No model inference or clinical approval.</p>
<p>Nine fixed, label-independent planes per exam (25%, 50%, 75% along each canonical axis). Image window: nonzero volume p1/p99. Original slice pixels retained; display size may differ. Sparse views can miss errors; full-volume expert review remains necessary.</p><nav>'''+navigation+'</nav>'+''.join(sections)+'''<script>document.getElementById('toggle').onclick=function(){const hidden=document.body.classList.toggle('hide');this.textContent=hidden?'Show mask overlays':'Hide mask overlays';this.setAttribute('aria-pressed',String(!hidden));};</script></html>'''
    (args.output/'index.html').write_text(page,encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps({'purpose':'Sparse technical alignment review aid','evaluation_ready':False,'expert_reviews_completed':0,'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),'exams':cases},indent=2)+'\n')


if __name__ == '__main__':
    main()
