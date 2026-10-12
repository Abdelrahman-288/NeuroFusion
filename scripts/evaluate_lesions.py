"""Analyze saved validation predictions with a fixed, explicitly defined protocol."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import sys
import nibabel as nib
import numpy as np
import scipy
from neurofusion.cohort import StudyStore,digest
from neurofusion.data import save_json
from neurofusion.lesions import lesion_metrics
from neurofusion.segmentation import metrics


def totals(results):
    keys=['reference_lesions','predicted_components','matched_pairs','missed_reference_lesions',
          'unmatched_predicted_components','no_overlap_predicted_components']
    result={k:sum(r[k] for r in results) for k in keys}
    nr,npred,tp=result['reference_lesions'],result['predicted_components'],result['matched_pairs']
    result.update(lesion_recall=tp/nr if nr else None,lesion_precision=tp/npred if npred else None,
                  lesion_f1=2*tp/(nr+npred) if nr+npred else None,
                  unmatched_components_per_scan=result['unmatched_predicted_components']/len(results))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','manifest','splits','cache','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output directory')
    config=json.loads((args.run/'config.json').read_text())
    summary=json.loads((args.run/'summary.json').read_text())
    previous=json.loads((args.run/'coverage-verification.json').read_text())
    if not previous['passed'] or digest(args.run/'last.pt')!=previous['last_checkpoint_sha256']:
        parser.error('Completed-run verification/checkpoint identity mismatch')
    if digest(args.manifest)!=config['manifest_sha256'] or digest(args.splits)!=config['splits_sha256']:
        parser.error('Dataset binding differs from the evaluated run')
    store=StudyStore(args.manifest,args.splits,args.cache)
    studies=store.studies('validation')
    if Counter(s['subject_id'] for s in studies)!=Counter(config['validation_subjects']):
        parser.error('Validation study set mismatch')
    old={c['subject']:c for c in summary['final_validation']['cases']}
    args.output.mkdir(parents=True)
    protocol={'probability_threshold':.5,'connectivity':26,'minimum_component_size_voxels':1,
        'primary_matching':'maximum-cardinality one-to-one, any positive voxel overlap',
        'sensitivity_checks':['same one-to-one matching with pair IoU >= 0.10','6-connectivity with any positive overlap'],
        'size_bins_ml':['[0,0.1)','[0.1,1)','[1,10)','[10,infinity)'],
        'notes':['Analyst-defined research metrics, not official ISLES evaluation.',
                 'Components touching diagonally join under 26-connectivity.',
                 'Any-overlap is permissive; a one-voxel intersection may count.',
                 'Maximum matching prevents one merged prediction from claiming multiple true positives.',
                 'Unmatched predictions include split fragments; no-overlap predictions are reported separately.',
                 'Equal-cardinality ties may change matched identities with library versions; versions and per-component matches are saved.',
                 'No threshold tuning, component filtering, retraining or holdout inference in this analysis.'],
        'scipy':scipy.__version__,'python':sys.version,'run':str(args.run.resolve()),
        'manifest_sha256':digest(args.manifest),'splits_sha256':digest(args.splits),
        'last_checkpoint_sha256':previous['last_checkpoint_sha256']}
    save_json(args.output/'protocol.json',protocol)
    cases=[]
    bins={k:{'reference_lesions':0,'matched':0,'no_overlap_missed':0} for k in ['<0.1 mL','0.1 to <1 mL','1 to <10 mL','>=10 mL']}
    missed=[];spurious=[]
    for i,study in enumerate(studies):
        subject=study['subject_id']
        _,reference,meta=store.load(study)
        path=args.run/'predictions'/f'{subject}-probability.nii.gz'
        image=nib.as_closest_canonical(nib.load(path))
        if image.shape!=reference.shape or not np.allclose(image.affine,meta['canonical_affine'],atol=1e-4,rtol=0) or image.header.get_xyzt_units()[0]!=meta['xyzt_units'][0]:
            raise ValueError('Prediction and reference geometry/units mismatch')
        probability=image.get_fdata(dtype=np.float32)
        voxel_result=metrics(probability,reference)
        if abs(voxel_result['dice']-old[subject]['dice'])>1e-7 or voxel_result['predicted_voxels']!=old[subject]['predicted_voxels']:
            raise ValueError('Saved prediction differs from original evaluation')
        scale={'mm':1.,'meter':1000.,'micron':.001}.get(meta['xyzt_units'][0])
        if scale is None:
            raise ValueError('Known spatial units required for size analysis')
        voxel_ml=abs(np.linalg.det(image.affine[:3,:3]))*scale**3/1000
        primary=lesion_metrics(probability,reference,voxel_ml)
        strict=lesion_metrics(probability,reference,voxel_ml,min_iou=.1)
        six=lesion_metrics(probability,reference,voxel_ml,connectivity=6)
        detail={'subject':subject,'prediction_sha256':digest(path),'voxel_metrics':voxel_result,
                'primary':primary,'iou_0_10':strict,'connectivity_6':six}
        save_json(args.output/'cases'/f'{subject}.json',detail)
        cases.append({'subject':subject,'dice':voxel_result['dice'],
                      **{k:v for k,v in primary.items() if not k.endswith('_details')},
                      'iou_0_10':{k:v for k,v in strict.items() if not k.endswith('_details')},
                      'connectivity_6':{k:v for k,v in six.items() if not k.endswith('_details')}})
        for lesion in primary['reference_details']:
            volume=lesion['volume_ml']
            key='<0.1 mL' if volume<.1 else '0.1 to <1 mL' if volume<1 else '1 to <10 mL' if volume<10 else '>=10 mL'
            bins[key]['reference_lesions']+=1
            bins[key]['matched']+=int(lesion['matched'])
            bins[key]['no_overlap_missed']+=int(not lesion['any_overlap'])
            if not lesion['any_overlap']:
                missed.append({'subject':subject,**lesion})
        for component in primary['prediction_details']:
            if not component['any_overlap']:
                spurious.append({'subject':subject,**component})
        if (i+1)%10==0:
            print(f'Analyzed {i+1}/{len(studies)} validation studies',flush=True)
    for row in bins.values():
        row['recall']=row['matched']/row['reference_lesions'] if row['reference_lesions'] else None
    aggregate=totals(cases)
    report={'validation_studies':len(cases),'holdout_evaluated':False,'primary':aggregate,
            'iou_0_10':totals([c['iou_0_10'] for c in cases]),
            'connectivity_6':totals([c['connectivity_6'] for c in cases]),
            'by_reference_size':bins,'cases':cases,
            'examples':{'largest_completely_missed':sorted(missed,key=lambda r:-r['volume_ml'])[:3],
                        'largest_no_overlap_prediction':sorted(spurious,key=lambda r:-r['volume_ml'])[:3]},
            'limitations':'Validation analysis only. Components are a voxel-topology approximation to lesions; no clinical adjudication or screening specificity.'}
    save_json(args.output/'summary.json',report)
    size_rows=''.join(f"<tr><td>{html.escape(k)}</td><td>{r['reference_lesions']}</td><td>{r['matched']}</td><td>{r['recall']:.1%}</td><td>{r['no_overlap_missed']}</td></tr>" for k,r in bins.items() if r['reference_lesions'])
    case_rows=''.join(f"<tr><td>{c['subject']}</td><td>{c['dice']:.3f}</td><td>{c['reference_lesions']}</td><td>{c['matched_pairs']}</td><td>{c['missed_reference_lesions']}</td><td>{c['unmatched_predicted_components']}</td></tr>" for c in sorted(cases,key=lambda c:-c['missed_reference_lesions']))
    (args.output/'index.html').write_text(f'''<!doctype html><meta charset="utf-8"><title>NeuroFusion lesion-level error analysis</title>
<style>body{{font:17px system-ui;max-width:1100px;margin:35px auto;padding:20px;color:#173348}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #dde;text-align:left}}.note{{background:#fff1cd;padding:16px}}</style>
<h1>Lesion-level validation analysis</h1><p>{len(cases)} studies · saved final-epoch predictions · threshold 0.5</p>
<p class="note">Research analysis, not the official challenge score. A lesion is a 26-connected reference component. Primary matching is one-to-one with any positive overlap; a one-voxel overlap can count. No holdout evaluation.</p>
<p><b>Recall {aggregate['lesion_recall']:.1%}</b> · Precision {aggregate['lesion_precision']:.1%} · F1 {aggregate['lesion_f1']:.3f} · {aggregate['unmatched_components_per_scan']:.1f} unmatched predicted components/scan</p>
<p>Matched {aggregate['matched_pairs']} of {aggregate['reference_lesions']} reference components; {aggregate['missed_reference_lesions']} unmatched reference components. Stricter pair IoU ≥0.10 recall: {report['iou_0_10']['lesion_recall']:.1%}. Six-connectivity recall: {report['connectivity_6']['lesion_recall']:.1%} (different component count).</p>
<h2>Detection by reference-component volume</h2><table><tr><th>Volume</th><th>Reference lesions</th><th>Matched</th><th>Recall</th><th>No overlap at all</th></tr>{size_rows}</table>
<h2>All validation studies, ordered by missed lesions</h2><table><tr><th>Subject</th><th>Voxel Dice</th><th>Reference</th><th>Matched</th><th>Unmatched reference</th><th>Unmatched predicted</th></tr>{case_rows}</table>
<p>Unmatched predicted components include split fragments, not just isolated spurious detections. No component filtering was applied. Equal-cardinality matching ties can affect size-bin allocation. <a href="protocol.json">Protocol</a> · <a href="summary.json">Complete results</a></p>''',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['cases','examples']},indent=2))


if __name__=='__main__':
    main()
