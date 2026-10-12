"""Validate controls and aggregate the complete paired-seed confirmation."""
from pathlib import Path
import json,hashlib
import numpy as np
from neurofusion.ucsf_confirmation import confirm_pairs
root=Path(__file__).resolve().parents[1];out=root/'experiments/ucsf-clipping-confirmation-001'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(out/'protocol.json');pairs={};provenance={};inventories={}
reference=root/'experiments/ucsf-specialist-train-002'
for seed in plan['seeds']:
    paths=[root/plan['controls'][str(seed)],root/'experiments'/(f'ucsf-clipping-seed{seed}-'+('002' if seed==44 else '001'))]
    reports=[]
    for mode,path in zip(('baseline','candidate'),paths):
        lr=.001
        protocol=read(path/'protocol.json');expected=read(reference/'protocol.json')
        expected['training_plan']['seed']=seed;expected['training_plan']['learning_rate']=lr
        if mode=='candidate':expected['training_plan']['gradient_clip_norm']=1.0
        if protocol!=expected:raise ValueError('Uncontrolled protocol change')
        for filename in ('partitions.json','cache-manifest.json'):
            if sha(path/filename)!=sha(reference/filename):raise ValueError('Partition/cache changed')
        for filename in ('tumor_segmentation.py','ucsf_loader.py','ucsf_validation.py','native_metrics.py','external_adapter.py'):
            if sha(path/'source'/filename)!=sha(reference/'source'/filename):raise ValueError('Shared implementation changed')
        report=read(path/'summary.json')
        if report['completed_epochs']!=5 or report['active_model_changed']:raise ValueError('Unexpected run status')
        for name,checksum in report['checkpoints'].items():
            if sha(path/name)!=checksum:raise ValueError('Checkpoint checksum mismatch')
        if mode=='candidate':
            verification=read(path/'verification.json')
            if len(verification['reloaded_final_masks_and_metrics_exact'])!=4:raise ValueError('Reload verification incomplete')
            for epoch in read(path/'history.json'):
                if epoch['max_post_clip_gradient_l2']>1.00001:raise ValueError('Clipping bound violated')
                if epoch['unique_slice_draws']!=2480 or epoch['positive_draws']!=1015:raise ValueError('Training coverage changed')
        provenance[str(path.relative_to(root))]={'summary_sha256':sha(path/'summary.json'),'final_checkpoint_sha256':report['checkpoints']['epoch-05.pt']}
        reports.append(report)
    pairs[seed]=tuple(reports);inventories[str(seed)]=[str(p.relative_to(root)) for p in paths]
result=confirm_pairs(pairs)
result['run_paths']=inventories
result['empty_states_by_seed']={str(seed):{name:report['final_epoch']['aggregate']['empty_states'] for name,report in zip(('baseline','candidate'),reports)} for seed,reports in pairs.items()}
result['mean_across_seeds']={key:float(np.mean([s['means'][key] for s in result['seeds'].values()])) for key in ('baseline_dice','candidate_dice','baseline_iou','candidate_iou','baseline_fp_ml','candidate_fp_ml')}
result['limitations']=['Three seeds on the same four development patients are not twelve independent patients','Clipping was selected after reviewing an epoch-five failure; this is reused development data','No independent external evaluation or expert approval','No retrospective checkpoint or seed selection']
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
provenance['confirmation_protocol_sha256']=sha(out/'protocol.json');provenance['comparison_script_sha256']=sha(Path(__file__))
for name in ('ucsf_confirmation.py','ucsf_sampling.py'):
    source=root/'src/neurofusion'/name
    provenance[name]=sha(source)
    (out/name).write_bytes(source.read_bytes())
(out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
(out/'comparison-script.py').write_bytes(Path(__file__).read_bytes())
rows=''.join(f'<tr><td>{seed}</td><td>{r["means"]["baseline_dice"]:.4f}</td><td>{r["means"]["candidate_dice"]:.4f}</td><td>{r["means"]["baseline_fp_ml"]:.3f}</td><td>{r["means"]["candidate_fp_ml"]:.3f}</td><td>{sum(r["gates"].values())}/4</td></tr>' for seed,r in result['seeds'].items())
sections=[]
for seed,r in result['seeds'].items():
    gates=''.join(f'<li>{key.replace("_"," ")}: {"PASS" if ok else "FAIL"}</li>' for key,ok in r['gates'].items())
    patients=''.join(f'<tr><td>{p["patient_id"]}</td><td>{p["baseline_dice"]:.4f}</td><td>{p["candidate_dice"]:.4f}</td><td>{p["dice_delta"]:+.4f}</td></tr>' for p in r['patients'])
    sections.append(f'<h2>Seed {seed}</h2><ul>{gates}</ul><div class="scroll"><table><tr><th>Patient</th><th>Baseline Dice</th><th>Candidate Dice</th><th>Change</th></tr>{patients}</table></div>')
(out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UCSF clipping confirmation</title><style>body{font:17px system-ui;background:#101b2b;color:#ecf3fb;max-width:1100px;margin:30px auto;padding:20px}td,th{padding:12px;border-bottom:1px solid #456;text-align:left}a{color:#80ded0}table{border-collapse:collapse}.scroll{overflow:auto}</style><h1>UCSF: clipping from initialization</h1>'''+f'<h2>{result["decision"]}</h2><p>Adam 0.001 in both arms; finite-gradient L2 clipping 1.0 versus no clipping. Original uniform sampling, identical patient split, five epochs, final checkpoint. All four gates must pass separately for every seed.</p><div class="scroll"><table><tr><th>Seed</th><th>Baseline Dice</th><th>Clipped Dice</th><th>Baseline FP mL</th><th>Clipped FP mL</th><th>Checks passed</th></tr>'+rows+'</table></div>'+''.join(sections)+'<p>These runs reuse the same four development patients. They measure training randomness, not independent generalization. Clipping was chosen after inspecting a failed trajectory. No active application model was changed. A zero-overlap or empty-output baseline is not useful simply because it generates fewer false positives; all gate failures remain visible.</p><p><a href="summary.json">Full comparison</a> · <a href="protocol.json">Predeclared rules</a> · <a href="provenance.json">Provenance</a></p></html>',encoding='utf-8')
print(json.dumps({'decision':result['decision'],'seeds':{k:{'means':v['means'],'gates':v['gates']} for k,v in result['seeds'].items()}},indent=2))
