"""Audit final UCSF predictions and render three-plane error overlays."""
import hashlib,json
from pathlib import Path
import nibabel as nib
import numpy as np
from PIL import Image
from neurofusion.native_metrics import native_binary_metrics
from neurofusion.segmentation_errors import component_errors
from neurofusion.specialist_plan import numeric_foreground

root=Path(__file__).resolve().parents[1]
run=root/'experiments/ucsf-specialist-train-002'
out=root/'experiments/ucsf-specialist-errors-001'
out.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parts=read(run/'partitions.json');summary=read(run/'summary.json');cases=[];sections=[]
for item in summary['final_epoch']['cases']:
    exam=item['exam_id'];record=next(r for r in parts['records'] if r['exam_id']==exam)
    paths={k:root/'data/raw/ucsf-pdgm-v5'/record[k]['path'] for k in ('image','mask')}
    for key,path in paths.items():
        if sha(path)!=record[key]['sha256']:raise ValueError('Source checksum mismatch')
    paths['prediction']=run/(exam+'-prediction.nii.gz')
    image,reference,prediction=[nib.load(paths[k]) for k in ('image','mask','prediction')]
    truth=nib.Nifti1Image(numeric_foreground(reference.get_fdata()).astype(np.uint8),reference.affine,reference.header.copy())
    metrics=native_binary_metrics(prediction,truth)
    if metrics!=item['metrics']:raise ValueError('Saved predictions differ from training metrics')
    if image.shape!=reference.shape or not np.allclose(image.affine,reference.affine):raise ValueError('Image grid mismatch')
    image,truth,prediction=[nib.as_closest_canonical(v) for v in (image,truth,prediction)]
    if not np.allclose(image.affine[:3,:3],np.diag(np.diag(image.affine[:3,:3])),atol=1e-4):raise ValueError('Oblique grid unsupported')
    values=image.get_fdata(dtype=np.float32);r=truth.get_fdata().astype(bool);p=prediction.get_fdata().astype(bool)
    errors=component_errors(p,r)
    low,high=np.percentile(values[values!=0],[1,99]);gray=np.rint(np.where(values!=0,np.clip((values-low)/(high-low),0,1),0)*255).astype(np.uint8)
    fn=r&~p;fp=p&~r;tp=r&p;directory=out/exam;directory.mkdir();cards=[];views=[]
    spacing=nib.affines.voxel_sizes(image.affine)
    for axis,name,directions in [(0,'Sagittal','left P / right A; top S'),(1,'Coronal','left L / right R; top S'),(2,'Axial','left L / right R; top A')]:
        axes=tuple(i for i in range(3) if i!=axis)
        indices={round((values.shape[axis]-1)*q):'fixed fraction' for q in (.25,.5,.75)}
        peak=int(np.argmax(fn.sum(axis=axes)))
        indices[peak]=indices.get(peak,'')+' / most missed voxels (annotation-selected)'
        for index,reason in sorted(indices.items()):
            plane=np.rot90(np.take(gray,index,axis=axis));base=np.repeat(plane[:,:,None],3,axis=2)
            overlay=np.zeros((*plane.shape,4),dtype=np.uint8)
            for mask,color in [(tp,(65,215,145)),(fn,(255,85,90)),(fp,(255,192,55))]:
                overlay[np.rot90(np.take(mask,index,axis=axis))]=(*color,165)
            stem=f'{axis}-{index}';Image.fromarray(base).save(directory/(stem+'.png'));Image.fromarray(overlay).save(directory/(stem+'-overlay.png'))
            ratio=plane.shape[1]*spacing[axes[0]]/(plane.shape[0]*spacing[axes[1]])
            cards.append(f'<figure><div class="slice" style="aspect-ratio:{ratio}"><img src="{exam}/{stem}.png" alt="{name} MRI"><img class="overlay" src="{exam}/{stem}-overlay.png" alt="Prediction errors"></div><figcaption>{name} {index}: {directions}<br>{reason}</figcaption></figure>')
            views.append({'axis':axis,'index':index,'selection':reason})
    cases.append({'exam_id':exam,'metrics':metrics,'errors':errors,'views':views,'source_sha256':{k:sha(v) for k,v in paths.items()}})
    sections.append(f'<section><h2>{exam} · Dice {metrics["dice"]:.3f}</h2><p>Missed annotation voxels: {errors["false_negative_voxels"]:,}. Extra prediction voxels: {errors["false_positive_voxels"]:,}. Reference components with zero overlap: {errors["reference_components_without_overlap"]}/{len(errors["reference_components"])}.</p><div class="grid">'+''.join(cards)+'</div></section>')
result={'purpose':'Development error analysis, not independent clinical evaluation','checkpoint_sha256':summary['checkpoints']['epoch-05.pt'],'cases':cases,'expert_reviews_completed':0,'component_policy':'26-connected numeric foreground; any voxel overlap is a permissive technical match, not lesion detection','slice_policy':'three fixed fractions plus maximum false-negative area on each axis; selected error views are not representative samples'}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
(out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>UCSF prediction error review</title><style>body{font:16px system-ui;background:#101b2b;color:#ecf3fb;max-width:1200px;margin:24px auto;padding:16px}header{position:sticky;top:0;background:#101b2b;z-index:2;padding:12px}button{padding:10px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.slice{position:relative;background:black}.slice img{position:absolute;width:100%;height:100%;inset:0}figure{margin:0}figcaption{padding:8px}body.hide .overlay{display:none}a{color:#80dccc}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style><header><h1>UCSF prediction errors</h1><button id="toggle" aria-pressed="true">Hide overlays</button><p><span style="color:#41d791">Green: overlap</span> · <span style="color:#ff555a">Red: missed annotation</span> · <span style="color:#ffc037">Amber: extra prediction</span></p></header><p>Final epoch, threshold 0.5. Four development patients; no independent test or expert approval. Numeric annotation union only. Nine fixed planes plus the plane with most missed voxels in each direction. These additional views deliberately highlight errors; sparse views can still miss problems.</p><p>Components use 26-connectivity and any-voxel overlap; they do not represent clinically verified lesions. <a href="summary.json">Full counts and provenance</a></p>'''+''.join(sections)+'''<script>document.getElementById('toggle').onclick=function(){const hidden=document.body.classList.toggle('hide');this.textContent=hidden?'Show overlays':'Hide overlays';this.setAttribute('aria-pressed',String(!hidden));};</script></html>''',encoding='utf-8')
(out/'provenance.json').write_text(json.dumps({str(p.relative_to(root)):sha(p) for p in [Path(__file__),root/'src/neurofusion/segmentation_errors.py',run/'summary.json',run/'partitions.json']},indent=2),encoding='utf-8')
print(json.dumps([{'exam':c['exam_id'],'missed':c['errors']['reference_components_without_overlap'],'reference_components':len(c['errors']['reference_components']),'extra':c['errors']['prediction_components_without_overlap'],'prediction_components':len(c['errors']['prediction_components'])} for c in cases],indent=2))
