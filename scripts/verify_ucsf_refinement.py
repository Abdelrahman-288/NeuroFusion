"""Verify all refinement checkpoints, native masks and paired decisions."""
import json
from pathlib import Path
import tempfile
import nibabel as nib
import numpy as np
import torch
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.ucsf_loader import UCSFSlices
from neurofusion.tumor_segmentation import TumorUNet
from neurofusion.ucsf_confirmation import confirm_pairs
from refine_ucsf_specialist import evaluate

root=Path(__file__).resolve().parents[1];run=root/'experiments/ucsf-refinement-001'
read=lambda p:json.loads(p.read_text())
protocol=read(run/'protocol.json');summary=read(run/'summary.json')
if digest(root/'scripts/refine_ucsf_specialist.py')!=protocol['source_sha256']:raise ValueError('Runner changed')
cache=root/'experiments/ucsf-specialist-cache-001';source=root/'data/raw/ucsf-pdgm-v5'
partition=root/'experiments/ucsf-specialist-plan-001/partitions.json'
if digest(partition)!=protocol['partitions_sha256'] or digest(cache/'manifest.json')!=protocol['cache_manifest_sha256']:raise ValueError('Data plan changed')
manifest=read(cache/'manifest.json');records={r['exam_id']:r for r in read(partition)['records']}
val=UCSFSlices(cache,'development_validation');torch.set_num_threads(2)
pairs={};verified=[];hashes={}
for seed in (42,43,44):
    folder=run/f'seed{seed}'
    history=read(folder/'history.json')
    if len(history)!=5 or any(h['unique_slices']!=2480 for h in history):raise ValueError('Training coverage differs')
    for epoch in range(1,6):
        path=folder/f'epoch-{epoch:02d}.pt';checkpoint=torch.load(path,map_location='cpu',weights_only=True)
        if checkpoint['epoch']!=epoch or checkpoint['protocol_sha256']!=digest(run/'protocol.json'):raise ValueError('Checkpoint protocol differs')
        if any(g['lr']!=.0003 for g in checkpoint['optimizer_state_dict']['param_groups']):raise ValueError('Learning rate differs')
        hashes[str(path.relative_to(root))]=digest(path)
    expected=next(r['checkpoint_sha256'] for r in summary['verification'] if r['seed']==seed)
    if digest(folder/'epoch-05.pt')!=expected:raise ValueError('Final checkpoint changed')
    model=TumorUNet().cuda();model.load_state_dict(checkpoint['model_state_dict'])
    with tempfile.TemporaryDirectory(prefix='ucsf-replay-') as temp:
        replay=evaluate(model,val,manifest,records,source,cache,Path(temp))
        if replay['cases']!=history[-1]['cases']:raise ValueError('Metrics replay differs')
        for case in replay['cases']:
            name=case['exam_id']+'-prediction.nii.gz';a=nib.load(folder/name);b=nib.load(Path(temp)/name)
            if not np.array_equal(a.get_fdata(),b.get_fdata()) or not np.array_equal(a.affine,b.affine):raise ValueError('Saved mask differs')
            verified.append(dict(seed=seed,exam=case['exam_id'],mask_sha256=digest(folder/name)))
    control=root/'experiments'/f'ucsf-clipping-seed{seed}-{"002" if seed==44 else "001"}'
    if digest(control/'epoch-05.pt')!=protocol['initial_checkpoints'][str(seed)]:raise ValueError('Control changed')
    pairs[seed]=(read(control/'summary.json'),read(folder/'summary.json'))
replayed=confirm_pairs(pairs)
for seed,row in replayed['seeds'].items():
    for key,value in row['gates'].items():
        if summary['seeds'][seed]['gates'][key]!=value:raise ValueError('Acceptance decision differs')
out=run/'verification.json'
if out.exists():raise ValueError('Verification already exists')
save_json(out,dict(passed=True,checkpoints_verified=15,masks_and_metrics_reproduced=verified,
    checkpoint_hashes=hashes,summary_sha256=digest(run/'summary.json'),protected_cohort_used=False))
print('Verified 15 checkpoints and all 12 native masks and metric dictionaries.')
