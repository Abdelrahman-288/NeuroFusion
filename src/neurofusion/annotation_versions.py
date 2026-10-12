"""Hash-bound dataset label versions with frozen development roles."""
import json,zipfile,hashlib
from pathlib import Path
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.model_registry import bound_file


def binding(root,path):
    path=Path(path).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root):raise ValueError('Artifact outside project')
    return dict(path=path.relative_to(root).as_posix(),sha256=digest(path))


def validate_version(root,record):
    path=bound_file(root,record);v=json.loads(path.read_text())
    if v.get('schema_version')!=1 or v.get('protected_data_used') is not False:raise ValueError('Invalid annotation version')
    for b in v['source_bindings']:bound_file(root,b)
    if v.get('parent'):bound_file(root,v['parent'])
    if v.get('approved_export'):bound_file(root,v['approved_export'])
    seen=set();groups={'train':set(),'validation':set()}
    for r in v['records']:
        if r['partition'] not in groups or r['id'] in seen:raise ValueError('Invalid or duplicate annotation role')
        seen.add(r['id']);groups[r['partition']].add(r['group'])
        bound_file(root,r['image'])
        if 'mask' in r:bound_file(root,r['mask'])
    if not all(groups.values()) or groups['train']&groups['validation']:raise ValueError('Annotation groups cross development partitions')
    return v


def apply_approved_export(root,output,records,export):
    """Import actual adjudicated binary masks only if their source is already train."""
    by_hash={}
    for r in records:by_hash.setdefault(r['image']['sha256'],[]).append(r)
    changed=set()
    with zipfile.ZipFile(export) as archive:
        if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('Duplicate ZIP entries')
        if sum(i.file_size for i in archive.infolist())>256*1024*1024:raise ValueError('Export too large')
        manifest=json.loads(archive.read('manifest.json'))
        if not manifest['records']:raise ValueError('Empty approved export')
        for item in manifest['records']:
            approval=item['adjudication']
            if approval.get('decision')!='approve' or approval.get('whole_volume_reviewed') is not True:raise ValueError('Unapproved annotation')
            checksum=approval.get('image_sha256');matches=by_hash.get(checksum,[])
            if len(matches)!=1 or matches[0]['partition']!='train':raise ValueError('Approved source is not an unambiguous training case')
            r=matches[0]
            if 'mask' not in r or r['id'] in changed:raise ValueError('Unsupported or duplicate correction')
            if not any(f['sha256']==checksum for f in item['source_files']):raise ValueError('Approval source binding differs')
            data=archive.read(item['label_path']);sha=hashlib.sha256(data).hexdigest()
            if sha!=item['label_sha256'] or sha!=approval['mask_sha256']:raise ValueError('Approved mask changed')
            suffix='.nii' if item['label_path'].endswith('.nii') else '.png' if item['label_path'].endswith('.png') else None
            if suffix is None:raise ValueError('Unsupported annotation format')
            folder=output/'labels';folder.mkdir(exist_ok=True);path=folder/(sha+suffix)
            if not path.exists():path.write_bytes(data)
            r['original_mask']=r['mask'];r['mask']=binding(root,path)
            r['annotation_origin']='approved_export';r['approval']=approval;changed.add(r['id'])
    return len(changed)


def freeze(root,key,output,parent=None,export=None):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root):raise ValueError('Version must stay in project')
    output.mkdir(parents=True,exist_ok=False);records=[]
    if key in ('tumor_classifier','tumor_segmenter'):
        base=root/'data/raw/brisc-v6/brisc2025';split=root/'experiments/brisc-curated-001/splits.json'
        publisher=base/'manifest.json';published={r['relative_path'].replace('\\','/'):r for r in json.loads(publisher.read_text())}
        for r in json.loads(split.read_text())['assignments']:
            if r['partition'] not in ('train','validation') or r['task']!='classification' or r['is_mask']:continue
            if key=='tumor_segmenter' and r['label']=='no_tumor':continue
            row=dict(id=r['path'],partition=r['partition'],group=r['group_id'],
                image=dict(path=(base/r['path']).relative_to(root).as_posix(),sha256=r['sha256']),
                class_label=r['label'],annotation_origin='publisher')
            if key=='tumor_segmenter':
                name=f"segmentation_task/{r['source_split']}/masks/{Path(r['path']).stem}.png"
                row['mask']=dict(path=(base/name).relative_to(root).as_posix(),sha256=published[name]['sha256'])
            records.append(row)
        sources=[binding(root,split),binding(root,publisher)]
    elif key=='stroke_dwi':
        from neurofusion.cohort import StudyStore
        manifest=root/'experiments/isles-curated-001/manifest.json';split=root/'experiments/isles-curated-001/frozen-splits-v1.json'
        store=StudyStore(manifest,split,root/'data/preprocessing-cache')
        for role in ('train','validation'):
            for s in store.studies(role):
                row=dict(id=s['subject_id'],group=s['subject_id'],partition=role,annotation_origin='publisher')
                for name,source in [('image','dwi'),('mask','mask')]:
                    f=s['files'][source];row[name]=dict(path=(store.root/f['path']).resolve().relative_to(root).as_posix(),sha256=f['sha256'])
                records.append(row)
        sources=[binding(root,manifest),binding(root,split)]
    else:raise ValueError('Unsupported model key')
    parent_binding=binding(root,parent) if parent else None
    if parent:
        previous=validate_version(root,parent_binding)
        if previous['model_key']!=key:raise ValueError('Parent model differs')
        if previous['source_bindings']!=sources:raise ValueError('Parent frozen sources differ')
        old={r['id']:r for r in previous['records']}
        if set(old)!={r['id'] for r in records}:raise ValueError('Parent coverage differs')
        for r in records:
            prior=old[r['id']]
            if any(prior[k]!=r[k] for k in ('partition','image','group')):raise ValueError('Parent roles changed')
        records=previous['records']
    corrections=apply_approved_export(root,output,records,export) if export else 0
    value=dict(schema_version=1,model_key=key,parent=parent_binding,source_bindings=sources,
        approved_export=binding(root,export) if export else None,corrections_in_version=corrections,
        protected_data_used=False,records=records,
        limitation='Publisher labels are not human approvals; review export approval does not authorize protected data or establish expertise')
    path=output/'annotations.json';save_json(path,value)
    validate_version(root,binding(root,path))
    return path
