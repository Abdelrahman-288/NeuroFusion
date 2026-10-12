"""Create a compact model/run card from measured completed-run artifacts."""
import argparse
import json
from pathlib import Path


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args()
output=args.run/'MODEL_CARD.md'
if output.exists():
    parser.error('Model card already exists')
summary=json.loads((args.run/'summary.json').read_text())
config=json.loads((args.run/'config.json').read_text())
inputs=' + '.join(config.get('inputs',['dwi'])).upper()
parameters=91633 if config.get('inputs')==['dwi','adc'] else 91417
validation=json.loads((args.run/'validation.json').read_text())
coverage=json.loads((args.run/'coverage-verification.json').read_text())
if not coverage['passed']:
    parser.error('Coverage check must pass first')
final=summary['final_validation']
best=max(validation,key=lambda v:v['mean_dice'])
ranked=sorted(final['cases'],key=lambda c:(c['dice'],c['subject']))
table='\n'.join(f"| {v['epoch']} | {v['mean_dice']:.4f} | {v['median_dice']:.4f} | {v['mean_absolute_volume_error_ml']:.2f} |" for v in validation)
examples='\n'.join(f"| {label} | {c['subject']} | {c['dice']:.4f} | {c['false_positive_voxels']} |" for label,c in
                   [('Lowest Dice',ranked[0]),('Middle-ranked',ranked[len(ranked)//2]),('Highest Dice',ranked[-1])])
rss=summary['peak_process_working_set_bytes']
memory=f'{rss/1024**3:.2f} GiB' if rss is not None else 'not measured'
text=f'''# NeuroFusion {inputs}: full-cohort run

Research development model. Not for diagnosis, screening or treatment decisions.
Inputs: compatible 3D {inputs} imaging. Output: a lesion-probability volume in the original
scan geometry. This model is limited to the ISLES development task; it does not
detect all brain abnormalities. Only the explicitly listed inputs are supported.

## Training and evaluation

- {summary['train_studies']} training studies; {summary['validation_studies']} validation studies.
- {summary['total_epochs']} epochs; {summary['steps']:,} patch updates; 32-cubed patches.
- Compact 3D U-Net ({parameters:,} parameters), mixed precision, BCE + soft Dice, Adam 0.001.
- Fixed probability threshold 0.5; full-volume overlapping-window validation.
- Sampling: {config['sampling']}.
- No holdout evaluation. No external-site or clinical validation.
- Two exact-image duplicate subjects were excluded; original data preserved.
- Mixed-site frozen partitions are not stratified; validation has no empty masks.

| Epoch | Mean Dice | Median Dice | Mean absolute volume error (mL) |
|---|---:|---:|---:|
{table}

The final epoch has mean Dice **{final['mean_dice']:.4f}**, median Dice
**{final['median_dice']:.4f}** and mean absolute volume error
**{final['mean_absolute_volume_error_ml']:.2f} mL**. Dice is segmentation overlap,
not diagnostic accuracy. Checkpoint selection uses mean validation Dice; the best
epoch was {best['epoch']}. Validation is development evidence, not an unbiased final test.

## Failure review

| Example selection | Subject | Final Dice | False-positive voxels |
|---|---|---:|---:|
{examples}

These examples are selected across the observed performance range, not randomly.
See `prediction-preview/index.html` for labeled reference/prediction slices.
Inspect full volumes before drawing case-level conclusions. Lesion-level detection
and specificity are not established by voxel Dice or a positive-case cohort.

## Resources and reproducibility

- Data preparation: {summary['preparation_seconds']/60:.1f} minutes.
- Training and validation: {summary['elapsed_training_validation_seconds']/60:.1f} minutes.
- Peak process working set: {memory}.
- PyTorch peak allocated GPU memory: {summary['peak_cuda_allocated_bytes']/1024**2:.1f} MiB.
  This excludes driver/context reservations and is not total GPU usage.
- Largest image/mask pair mapped at once: {summary['largest_loaded_image_and_mask_bytes']/1024**2:.1f} MiB.
- All expected study visits and prediction files passed coverage verification.
- Last checkpoint SHA256: `{coverage['last_checkpoint_sha256']}`.
- Source snapshot, hashes and package versions are saved in this run folder.

`predictions/` corresponds to the final epoch's `last.pt`, not necessarily `best.pt`.
Both checkpoints are retained. Raw source and cached inputs are fingerprinted.
Exact checkpoint continuation for this runner passed a separate synthetic control
comparison with the original voxel sampler; cross-machine bitwise equality is not guaranteed.

## Remaining limitations and next experiments

Native spacing changes the physical field of view between subjects. Training used
{inputs}, a short schedule and no augmentation. Errors vary substantially
by case. Review the separate lesion-analysis artifacts, when available, alongside
these voxel metrics before selecting further training changes.
Keep development on the existing training/validation sets; holdout remains unused.
'''
output.write_text(text,encoding='utf-8')
print(output)
