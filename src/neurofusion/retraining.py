"""Retrain the three supported architectures from a frozen annotation version."""
import json
from pathlib import Path
import numpy as np
import nibabel as nib
from PIL import Image
import torch
from neurofusion.annotation_versions import binding,validate_version
from neurofusion.data import save_json
from neurofusion.inference import MODELS,load_model_checkpoint,prepare_dwi_input
from neurofusion.model_registry import active_models,GATES,bound_file
from neurofusion.tumor import CLASSES
from neurofusion.tumor_segmentation import binary_mask,native_probability,segmentation_loss
from neurofusion.segmentation import sample_patch,predict_volume,metrics,segmentation_loss as stroke_loss


def load_case(root,key,row):
    image=bound_file(root,row['image'])
    if key=='stroke_dwi':
        x,meta=prepare_dwi_input(image);mask=nib.load(bound_file(root,row['mask']))
        if mask.shape!=tuple(meta['original_shape']) or mask.header.get_xyzt_units()[0]!='mm' or not np.allclose(mask.affine,meta['original_affine'],rtol=0,atol=1e-4):raise ValueError('Annotation grid differs from source')
        y=nib.as_closest_canonical(mask).get_fdata(dtype=np.float32)
        if not np.isin(y,[0,1]).all():raise ValueError('DWI annotations must be binary')
        return x,y,y
    with Image.open(image) as im:
        shape=(im.height,im.width);x=np.asarray(im.convert('L').resize((128,128),Image.Resampling.BILINEAR)).copy()[None].astype(np.float32)/255
    if key=='tumor_classifier':return x,CLASSES.index(row['class_label']),None
    with Image.open(bound_file(root,row['mask'])) as im:
        if im.mode!='L':raise ValueError('Expected grayscale annotation')
        native=binary_mask(np.asarray(im))
    if native.shape!=shape:raise ValueError('Annotation dimensions differ from source')
    y=np.asarray(Image.fromarray(native).resize((128,128),Image.Resampling.NEAREST)).copy()[None].astype(np.float32)
    return x,y,native


def train(root,version_path,output,epochs=1,seed=20261011):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root) or not 1<=epochs<=100:raise ValueError('Invalid run output/epochs')
    version_binding=binding(root,version_path);version=validate_version(root,version_binding);key=version['model_key']
    output.mkdir(parents=True,exist_ok=False)
    relative,sha=active_models(root,MODELS)[key];base_binding=dict(path=relative,sha256=sha)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    torch.set_num_threads(2);torch.manual_seed(seed);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;rng=np.random.default_rng(seed)
    protocol=dict(schema_version=1,model_key=key,annotation_version=version_binding,baseline=base_binding,
        seed=seed,epochs=epochs,learning_rate=.0001,batch_size=16 if key!='stroke_dwi' else 1,
        patches_per_training_volume=2,threshold=.5,training_partition='train',protected_data_used=False,
        selection='Final epoch only; all frozen validation cases; no threshold or checkpoint search',
        development_rule='Classifier accuracy nondecreasing; segmentation mean Dice nondecreasing, mean false-positive count nonincreasing, no new zero-overlap cases',
        device=device,torch=str(torch.__version__))
    save_json(output/'protocol.json',protocol);protocol_binding=binding(root,output/'protocol.json')
    training=[r for r in version['records'] if r['partition']=='train'];validation=[r for r in version['records'] if r['partition']=='validation']
    save_json(output/'training-manifest.json',dict(annotation_version=version_binding,training_partition='train',protected_data_used=False,records=training))
    manifest_binding=binding(root,output/'training-manifest.json')
    model=load_model_checkpoint(key,root/relative,sha).to(device);baseline=load_model_checkpoint(key,root/relative,sha).to(device).eval()
    optimizer=torch.optim.Adam(model.parameters(),lr=.0001)
    # Validate every label and geometry before starting an optimizer update.
    cache={}
    for row in version['records']:
        loaded=load_case(root,key,row)
        if key!='stroke_dwi':cache[row['id']]=loaded
    print('Validated annotation version',len(training),'train /',len(validation),'validation',flush=True)
    history=[]
    for epoch in range(epochs):
        model.train();losses=[];visited=[];order=rng.permutation(len(training))
        step=16 if key!='stroke_dwi' else 1
        for start in range(0,len(order),step):
            batch=[training[i] for i in order[start:start+step]];visited.extend(r['id'] for r in batch)
            repeats=2 if key=='stroke_dwi' else 1
            for _ in range(repeats):
                if key=='stroke_dwi':
                    x,y,_=load_case(root,key,batch[0]);x,y=sample_patch(x,y,rng);x=x[None,None];y=y[None,None]
                else:
                    x=np.stack([cache[r['id']][0] for r in batch]);y=np.asarray([cache[r['id']][1] for r in batch])
                tx=torch.from_numpy(x).to(device);ty=torch.as_tensor(y,device=device)
                optimizer.zero_grad(set_to_none=True);logits=model(tx)
                loss=torch.nn.functional.cross_entropy(logits,ty.long()) if key=='tumor_classifier' else (stroke_loss if key=='stroke_dwi' else segmentation_loss)(logits,ty.float())
                if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);optimizer.step();losses.append(float(loss.detach()))
        if sorted(visited)!=sorted(r['id'] for r in training):raise ValueError('Training coverage mismatch')
        history.append(dict(epoch=epoch+1,mean_batch_loss=float(np.mean(losses)),training_cases=len(visited)))
        print(history[-1],flush=True)
    checkpoint=output/'last.pt'
    torch.save(dict(model=model.state_dict(),annotation_version=version_binding,protocol=protocol_binding,training_manifest=manifest_binding,history=history),checkpoint)
    checkpoint_binding=binding(root,checkpoint);reloaded=load_model_checkpoint(key,checkpoint,checkpoint_binding['sha256']).to(device).eval();model.eval()
    cases=[];replay_max=0.;predictions=output/'predictions';predictions.mkdir()
    with torch.inference_mode():
        for i,row in enumerate(validation):
            x,y,native=load_case(root,key,row) if key=='stroke_dwi' else cache[row['id']]
            def predict(m):
                if key=='stroke_dwi':return predict_volume(m,x,device)
                result=m(torch.from_numpy(x[None]).to(device))
                return result.softmax(1)[0].cpu().numpy() if key=='tumor_classifier' else result.sigmoid()[0,0].cpu().numpy()
            candidate=predict(model);control=predict(baseline);replay=predict(reloaded)
            replay_max=max(replay_max,float(np.max(np.abs(candidate-replay))))
            file=predictions/f'{i:04d}.npz';np.savez_compressed(file,candidate=candidate,baseline=control)
            if key=='tumor_classifier':score=dict(candidate_correct=int(candidate.argmax()==y),baseline_correct=int(control.argmax()==y))
            else:
                if key=='tumor_segmenter':candidate=native_probability(candidate,native.shape);control=native_probability(control,native.shape)
                a=metrics(candidate,native);b=metrics(control,native)
                score=dict(candidate_dice=a['dice'],baseline_dice=b['dice'],candidate_fp=a['false_positive_voxels'],baseline_fp=b['false_positive_voxels'],new_zero_overlap=a['dice']==0 and b['dice']>0)
            cases.append(dict(id=row['id'],partition='validation',prediction=binding(root,file),**score))
    if key=='tumor_classifier':quality=np.mean([c['candidate_correct'] for c in cases])>=np.mean([c['baseline_correct'] for c in cases])
    else:quality=np.mean([c['candidate_dice'] for c in cases])>=np.mean([c['baseline_dice'] for c in cases]) and np.mean([c['candidate_fp'] for c in cases])<=np.mean([c['baseline_fp'] for c in cases]) and not any(c['new_zero_overlap'] for c in cases)
    save_json(output/'validation.json',cases)
    checks=dict.fromkeys(GATES,False);checks.update(development_quality=bool(quality),input_compatibility=True,prediction_reproduction=replay_max==0)
    run=dict(schema_version=1,model_key=key,checkpoint=checkpoint_binding,annotation_version=version_binding,
        protocol=protocol_binding,training_manifest=manifest_binding,validation=binding(root,output/'validation.json'),
        training_cases=len(training),validation_cases=len(validation),checks=checks,replay_max_difference=replay_max,
        missing_evidence=['independent_evaluation','uncertainty','robustness','regression_review'],protected_data_used=False)
    save_json(output/'training-run.json',run)
    return output/'training-run.json'


def assemble(root,run_path,output,gate_evidence=None):
    root=Path(root).resolve();run_binding=binding(root,run_path);run=json.loads(Path(run_path).read_text());checks=dict(run['checks']);supplements={}
    version=validate_version(root,run['annotation_version'])
    for name in ('checkpoint','protocol','training_manifest','validation'):bound_file(root,run[name])
    verify_training_coverage(root,version,run)
    for gate,path in (gate_evidence or {}).items():
        if gate not in run['missing_evidence']:raise ValueError('Unsupported supplemental gate')
        b=binding(root,path);e=json.loads(Path(path).read_text())
        if e.get('gate')!=gate or e.get('model_key')!=run['model_key'] or e.get('checkpoint_sha256')!=run['checkpoint']['sha256'] or e.get('annotation_version')!=run['annotation_version'] or e.get('protocol')!=run['protocol']:
            raise ValueError('Supplemental gate evidence binding differs')
        if not e.get('artifacts'):raise ValueError('Gate requires supporting artifacts')
        for artifact in e['artifacts']:bound_file(root,artifact)
        checks[gate]=e.get('passed') is True;supplements[gate]=b
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    evaluation=dict(model_key=run['model_key'],checkpoint_sha256=run['checkpoint']['sha256'],checks=checks,
        training_run=run_binding,supplemental_evidence=supplements)
    save_json(output/'evaluation.json',evaluation)
    report=dict(schema_version=2,model_key=run['model_key'],threshold=.5,checks=checks,
        checkpoint=run['checkpoint'],protocol=run['protocol'],training_manifest=run['training_manifest'],
        annotation_version=run['annotation_version'],training_run=run_binding,
        evaluation=binding(root,output/'evaluation.json'),training_partition='train',protected_data_used=False)
    save_json(output/'promotion.json',report)
    save_json(output/'decision.json',dict(eligible=all(checks.values()),failed_or_missing=[g for g in GATES if not checks[g]],active_model_changed=False))
    return output/'promotion.json'


def verify_training_coverage(root,version,run):
    manifest=json.loads(bound_file(root,run['training_manifest']).read_text())
    if manifest.get('training_partition')!='train' or manifest.get('protected_data_used') is not False or run.get('protected_data_used') is not False:
        raise ValueError('Training lineage must exclude protected data')
    if manifest['records']!=[r for r in version['records'] if r['partition']=='train']:raise ValueError('Training manifest coverage mismatch')
    cases=json.loads(bound_file(root,run['validation']).read_text())
    expected=[r['id'] for r in version['records'] if r['partition']=='validation']
    if [c['id'] for c in cases]!=expected or any(c['partition']!='validation' for c in cases):raise ValueError('Validation coverage differs from frozen version')
    for case in cases:bound_file(root,case['prediction'])


def validate_lineage(root,evidence,evaluation):
    if evidence.get('schema_version')!=2:raise ValueError('Versioned annotation/training lineage required')
    version=validate_version(root,evidence['annotation_version']);run=json.loads(bound_file(root,evidence['training_run']).read_text())
    if evaluation.get('training_run')!=evidence['training_run'] or version['model_key']!=evidence['model_key'] or run['model_key']!=evidence['model_key']:raise ValueError('Training lineage model mismatch')
    for key in ('checkpoint','annotation_version','protocol','training_manifest'):
        if run[key]!=evidence[key]:raise ValueError('Training lineage binding mismatch')
    protocol=json.loads(bound_file(root,evidence['protocol']).read_text());manifest=json.loads(bound_file(root,evidence['training_manifest']).read_text())
    if protocol['annotation_version']!=evidence['annotation_version'] or manifest['annotation_version']!=evidence['annotation_version']:raise ValueError('Training annotation version mismatch')
    if manifest['records']!=[r for r in version['records'] if r['partition']=='train']:raise ValueError('Training manifest coverage mismatch')
    verify_training_coverage(root,version,run)
    for gate in GATES:
        if gate in run['missing_evidence']:
            b=evaluation.get('supplemental_evidence',{}).get(gate)
            if b is None:raise ValueError('Missing gate evidence')
            g=json.loads(bound_file(root,b).read_text())
            if g.get('passed') is not True or g.get('gate')!=gate or g.get('model_key')!=evidence['model_key'] or g.get('checkpoint_sha256')!=evidence['checkpoint']['sha256'] or g.get('annotation_version')!=evidence['annotation_version'] or g.get('protocol')!=evidence['protocol']:raise ValueError('Gate evidence is not bound to training lineage')
            if not g.get('artifacts'):raise ValueError('Gate artifacts absent')
            for artifact in g['artifacts']:bound_file(root,artifact)
        elif run['checks'].get(gate) is not True:raise ValueError('Training evaluation gate failed')
