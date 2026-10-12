"""Check local tumor candidates without accessing protected test images."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.calibration import group_partition,fit_temperature,scale,metrics
from neurofusion.inference import MODELS,Predictor,load_model_checkpoint
from neurofusion.tumor import load_partition
from neurofusion.tumor_segmentation import load_segmentation,native_probability,mask_metrics
from neurofusion.tumor_uncertainty import binary_scale,binary_scores,selective_summary

ROOT=Path(__file__).resolve().parents[1]


def infer(model,images,device):
    result=[]
    with torch.inference_mode():
        for start in range(0,len(images),16):
            result.append(model(torch.from_numpy(images[start:start+16]).float().to(device)/255).cpu().numpy())
    return np.concatenate(result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    split=ROOT/'experiments/brisc-curated-001/splits.json';data=ROOT/'data/raw/brisc-v6/brisc2025'
    confirmation_path=ROOT/'experiments/tumor-continuation-confirmation-001/summary.json'
    confirmation=json.loads(confirmation_path.read_text())['records']
    protocol=dict(scope='Retrospective development qualification; validation previously reused',
        split_sha256=digest(split),confirmation_sha256=digest(confirmation_path),
        partition='validation',test_loaded=False,patient_independence=False,
        group_split='Existing calibration-v1 deterministic half of image-similarity groups',
        segmentation_temperature_grid=[.5,.75,1.,1.5,2.,3.,4.],
        pixel_sampling='4096 equally spaced flattened native-grid indices per image, including background',
        fit_objective='Mean sampled pixel NLL, equal weight per image',
        abstention='Fit-only 80th percentile uncertainty; evaluation coverage >=0.5 and risk no greater than all cases',
        segmentation_uncertainty='Mean calibrated binary entropy in predicted foreground; empty prediction = 1',
        uncertainty_checks='Evaluation NLL and Brier must not worsen; ECE <=0.05; selective-risk check must pass',
        compatibility='Supported loader, finite outputs, native geometry, saved probabilities within 1e-5, identical threshold masks',
        automatic_promotion=False,clinical_ready=False,device=device,
        source_sha256=digest(Path(__file__)))
    save_json(a.output/'protocol.json',protocol)
    images,_,native,rows=load_segmentation(data,split,'validation')
    fit=group_partition([r['group_id'] for r in rows]);ev=~fit
    save_json(a.output/'segmentation-partitions.json',dict(records=[dict(path=r['path'],group=r['group_id'],role='fit' if f else 'evaluation') for r,f in zip(rows,fit)]))
    results=[]
    for record in confirmation:
        run=ROOT/'experiments'/record['candidate_run'];checksum=record['candidate_checkpoint_sha256']
        config=json.loads((run/'config.json').read_text())
        if config['split_sha256']!=digest(split):raise ValueError('Candidate split changed')
        model=load_model_checkpoint('tumor_segmenter',run/'last.pt',checksum).to(device).eval()
        logits=infer(model,images,device)[:,0]
        probs=1/(1+np.exp(-np.clip(logits,-80,80)))
        saved=json.loads((run/'validation.json').read_text())
        if len(saved)!=len(rows):raise ValueError('Incomplete saved coverage')
        maxdiff=0.;changed_masks=0;sample_p=[];sample_y=[];dice=[];native_probs=[]
        for i,(r,old,truth) in enumerate(zip(rows,saved,native)):
            if (r['path'],r['group_id'])!=(old['path'],old['group_id']):raise ValueError('Prediction ordering differs')
            path=run/'predictions'/old['prediction']
            if digest(path)!=old['prediction_sha256']:raise ValueError('Saved probability changed')
            with np.load(path) as archive:reference=archive['probability']
            maxdiff=max(maxdiff,float(np.max(np.abs(reference-probs[i]))))
            probability=native_probability(probs[i],truth.shape)
            changed_masks+=int(not np.array_equal(probability>=.5,native_probability(reference,truth.shape)>=.5))
            indices=np.linspace(0,truth.size-1,4096,dtype=int)
            sample_p.append(probability.ravel()[indices]);sample_y.append(truth.ravel()[indices])
            native_probs.append(probability)
            dice.append(mask_metrics(probability,truth)['dice'])
        sample_p=np.asarray(sample_p);sample_y=np.asarray(sample_y)
        temperature=min(protocol['segmentation_temperature_grid'],key=lambda t:binary_scores(binary_scale(sample_p[fit],t),sample_y[fit])['nll'])
        before=binary_scores(sample_p[ev],sample_y[ev]);after=binary_scores(binary_scale(sample_p[ev],temperature),sample_y[ev])
        uncertainty=[];mask_changes=0
        for probability in native_probs:
            calibrated=binary_scale(probability,temperature)
            mask=probability>=.5;mask_changes+=int(not np.array_equal(mask,calibrated>=.5))
            q=np.clip(calibrated[mask],1e-12,1-1e-12)
            uncertainty.append(float((-(q*np.log2(q)+(1-q)*np.log2(1-q))).mean()) if q.size else 1.)
        uncertainty=np.asarray(uncertainty);dice=np.asarray(dice)
        selective=selective_summary(uncertainty[fit],uncertainty[ev],1-dice[ev])
        checks=dict(nll_not_worse=after['nll']<=before['nll']+1e-12,brier_not_worse=after['brier']<=before['brier']+1e-12,
            ece_at_most_0_05=after['ece']<=.05,selective_risk=selective['passed'])
        # Exercise the actual viewer code with this candidate in memory; no registry writes.
        viewer=Predictor(ROOT,device);viewer.registry=dict(MODELS)
        viewer.registry['tumor_segmenter']=(f'experiments/{record["candidate_run"]}/last.pt',checksum)
        output=viewer.analyze(data/rows[0]['path'],'tumor-image',a.output/f'viewer-seed{record["seed"]}')
        with np.load(a.output/f'viewer-seed{record["seed"]}/probability.npz') as archive:
            viewer_difference=float(np.max(np.abs(archive['probability']-native_probs[0])))
        compatibility=bool(maxdiff<=1e-5 and changed_masks==0 and viewer_difference<=1e-5 and mask_changes==0 and
                           output['models']['tumor_segmenter']==checksum and np.isfinite(probs).all())
        result=dict(seed=record['seed'],checkpoint_sha256=checksum,images=len(rows),fit_images=int(fit.sum()),evaluation_images=int(ev.sum()),
            compatibility_passed=compatibility,max_probability_difference=maxdiff,changed_native_masks=changed_masks,
            viewer_probability_difference=viewer_difference,temperature=temperature,before=before,after=after,
            selective=selective,uncertainty_checks=checks,uncertainty_passed=all(checks.values()),
            development_quality_passed=record['development_screen_passed'],independent_qualification=False,promotion_permitted=False)
        save_json(a.output/f'seed{record["seed"]}.json',result)
        np.savez_compressed(a.output/f'seed{record["seed"]}-evaluation.npz',sample_probability=sample_p,truth=sample_y,fit=fit,dice=dice,uncertainty=uncertainty)
        results.append(result);print(json.dumps(result),flush=True)
    # Classifier is unchanged: include its own calibration, not inferred from segmentation.
    x,y,class_rows=load_partition(data,split,'validation')
    class_fit=group_partition([r['group_id'] for r in class_rows]);class_ev=~class_fit
    relative,checksum=MODELS['tumor_classifier']
    model=load_model_checkpoint('tumor_classifier',ROOT/relative,checksum).to(device).eval()
    logits=infer(model,x,device);logits-=logits.max(1,keepdims=True);probs=np.exp(logits);probs/=probs.sum(1,keepdims=True)
    temperature=fit_temperature(probs[class_fit],y[class_fit]);calibrated=scale(probs,temperature)
    before=metrics(probs[class_ev],y[class_ev]);after=metrics(calibrated[class_ev],y[class_ev])
    uncertainty=1-calibrated.max(1);loss=(calibrated.argmax(1)!=y).astype(float)
    selective=selective_summary(uncertainty[class_fit],uncertainty[class_ev],loss[class_ev])
    checks=dict(nll_not_worse=after['nll']<=before['nll'],brier_not_worse=after['brier_multiclass_sum']<=before['brier_multiclass_sum'],
                ece_at_most_0_05=after['ece_10_equal_width']<=.05,selective_risk=selective['passed'])
    classification=dict(checkpoint_sha256=checksum,model_changed=False,temperature=temperature,before=before,after=after,
                        selective=selective,uncertainty_checks=checks,uncertainty_passed=all(checks.values()))
    save_json(a.output/'classifier.json',classification)
    np.savez_compressed(a.output/'classifier-evaluation.npz',probabilities=probs,labels=y,fit=class_fit)
    save_json(a.output/'classifier-partitions.json',dict(records=[dict(path=r['path'],group=r['group_id'],role='fit' if f else 'evaluation') for r,f in zip(class_rows,class_fit)]))
    summary=dict(checks_completed=True,segmentation=results,classifier=classification,
        independently_qualified=False,promotion_permitted=False,test_loaded=False,clinical_ready=False,
        blockers=['BRISC patient identities unavailable; image groups cannot prove patient independence',
                  'Validation reused during model development; this is not independent qualification',
                  'Segmentation evaluated on tumor-positive images only; screening specificity unestablished'])
    save_json(a.output/'summary.json',summary)
    (a.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Tumor qualification checks</title><h1>Tumor qualification checks</h1><p>Development checks completed; independent qualification blocked. No models promoted.</p><pre>'+json.dumps(summary,indent=2)+'</pre>',encoding='utf-8')
    print('Completed all tumor checks; independent qualification remains blocked.',flush=True)


if __name__=='__main__':main()
