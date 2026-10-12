"""Offline operational acceptance, separate from scientific qualification."""
import argparse
import json
from pathlib import Path

from neurofusion.cohort import digest
from neurofusion.inference import MODELS, Predictor
from neurofusion.model_registry import active_models

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    scope = json.loads((ROOT/'configs/release_scope.json').read_text())
    if scope['dataset_downloads_allowed'] is not False:
        raise ValueError('Existing-data release must disable downloads')
    inventory=[]
    for relative in scope['allowed_dataset_roots']:
        folder=ROOT/relative
        if not folder.is_dir():raise ValueError('Missing existing dataset: '+relative)
        files=[p for p in folder.rglob('*') if p.is_file()]
        if not files:raise ValueError('Empty dataset: '+relative)
        inventory.append(dict(root=relative, files=len(files), bytes=sum(p.stat().st_size for p in files)))
    eeg=json.loads((ROOT/'experiments/eeg-pilot-001/download-manifest.json').read_text())
    if len(eeg['records'])!=12:raise ValueError('Unexpected EEG pilot size')
    for row in eeg['records']:
        if digest(ROOT/'data/raw/chbmit-pilot'/row['path'])!=row['sha256']:
            raise ValueError('EEG source checksum mismatch')
    acquisition=ROOT/'experiments/ucsf-acquisition-001'
    acquired=json.loads((acquisition/'summary.json').read_text())
    if len(acquired['results'])!=20:raise ValueError('Unexpected protected cohort size')
    acquired_bytes=0
    for case in acquired['results']:
        for source_file in case['files']:
            source=acquisition/source_file['path']
            if digest(source)!=source_file['sha256']:raise ValueError('Protected source checksum mismatch')
            acquired_bytes+=source.stat().st_size
    inventory.append(dict(root=scope['existing_protected_cohort_root'],files=40,
                          bytes=acquired_bytes,role='protected; checksum checks only'))
    predictor=Predictor(ROOT,'cpu')
    model_checks=[]
    for key,(relative,expected) in active_models(ROOT,MODELS).items():
        model=predictor.model(key)
        model_checks.append(dict(model=key, path=relative, sha256=expected,
                                 parameters=sum(p.numel() for p in model.parameters())))
    # Only an already assigned training image is used for a functional smoke
    # check. Do not use protected test cases to verify the application.
    partitions=json.loads((ROOT/'experiments/brisc-curated-001/splits.json').read_text())
    row=next(r for r in partitions['assignments']
             if r['partition']=='train' and r['task']=='classification' and not r['is_mask'])
    source=ROOT/'data/raw/brisc-v6/brisc2025'/row['path']
    if digest(source)!=row['sha256']:raise ValueError('Training image checksum mismatch')
    result=predictor.analyze(source,'tumor-image',args.output/'tumor-smoke')
    if not result['research_only'] or len(result['views'])!=1:raise ValueError('Invalid smoke output')
    for view in result['views']:
        for field in ('image','overlay'):
            if not (args.output/'tumor-smoke'/view[field]).is_file():raise ValueError('Missing render')
    stroke_config=json.loads((ROOT/'experiments/dwi-component-001/config.json').read_text())
    manifest=json.loads((ROOT/'experiments/isles-curated-001/manifest.json').read_text())
    study=next(s for s in manifest['studies'] if s['subject_id'] in stroke_config['train_subjects'])
    dwi=study['files']['dwi']
    source=Path(manifest['data_root'])/dwi['path']
    if digest(source)!=dwi['sha256']:raise ValueError('DWI training source checksum mismatch')
    stroke=predictor.analyze(source,'stroke-dwi',args.output/'stroke-smoke')
    import nibabel as nib
    import numpy as np
    original=nib.load(source)
    probability=nib.load(args.output/'stroke-smoke'/stroke['probability_file'])
    if original.shape!=probability.shape or not np.allclose(original.affine,probability.affine):
        raise ValueError('Stroke probability not restored to original grid')
    summary=dict(scope='Offline operational check, not independent model evaluation',
                 passed=True, network_requests=0, dataset_inventory=inventory,
                 eeg_source_files_verified=12, loaded_models=model_checks,
                 tumor_training_image_smoke=True, protected_cohort_inference=False,
                 stroke_training_volume_smoke=True, stroke_original_grid_verified=True,
                 protected_ucsf_source_files_verified=40,
                 research_release_complete=False, clinical_ready=False)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
