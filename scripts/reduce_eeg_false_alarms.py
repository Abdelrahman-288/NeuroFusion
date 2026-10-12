"""Select an alarm policy on training recordings; evaluate fixed validation once."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,json
from pathlib import Path
import numpy as np
import torch
from train_eeg_pilot import SeizureCNN
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.eeg_alarms import score_policy,aggregate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];old=root/'experiments/eeg-pilot-001';out=args.output
    out.mkdir(parents=True,exist_ok=False);read=lambda p:json.loads(p.read_text())
    report=read(old/'summary.json');manifest=read(old/'prepared-manifest.json');records=manifest['records']
    if len(records)!=12 or digest(old/'last.pt')!=report['checkpoint_sha256']:raise ValueError('Pilot source changed')
    train=[r for r in records if r['partition']=='train'];validation=[r for r in records if r['partition']=='validation']
    if len(train)!=8 or len(validation)!=4 or {r['patient'] for r in train}&{r['patient'] for r in validation}:raise ValueError('Patient partition changed')
    protocol=dict(checkpoint_sha256=digest(old/'last.pt'),prepared_manifest_sha256=digest(old/'prepared-manifest.json'),
        thresholds=[.5,.65,.8,.9,.95,.99],consecutive_windows=[1,2,3,4],window_seconds=4,
        train_recordings=[r['path'] for r in train],validation_recordings=[r['path'] for r in validation],
        selection='Training only: preserve baseline matched and timely events on each patient; minimize false alarms, then background alarm seconds, then maximum timely latency, then shorter confirmation and lower threshold; baseline fallback',
        acceptance='Validation false alarms lower; no fewer matched or timely seizures overall or per patient; background alarm burden not higher',
        causal=True,refractory_suppression=False,checkpoint_retrained=False,validation_reused=True,
        limitations='Existing label-selected 12-recording pilot; fitting scores are from model-training patients; validation previously examined; no independent qualification')
    save_json(out/'protocol.json',protocol)
    torch.set_num_threads(2);device='cuda' if torch.cuda.is_available() else 'cpu';model=SeizureCNN().to(device)
    model.load_state_dict(torch.load(old/'last.pt',weights_only=True,map_location=device)['model']);model.eval()
    probabilities={};reproduction=[];hashes={}
    with torch.inference_mode():
        for row in records:
            if digest(root/'data/raw/chbmit-pilot'/row['path'])!=row['sha256'] or digest(old/row['prepared'])!=row['prepared_sha256']:raise ValueError('Source/feature checksum changed')
            pack=np.load(old/row['prepared'],allow_pickle=False)
            prob=np.concatenate([model(batch.to(device)).sigmoid().cpu().numpy() for batch in torch.from_numpy(pack['x']).split(128)])
            if row['partition']=='validation':
                prior=next(r for r in report['records'] if r['path']==row['path']);saved=old/prior['probabilities']
                if digest(saved)!=prior['probability_sha256']:raise ValueError('Historical predictions changed')
                reference=np.load(saved);delta=float(np.max(np.abs(prob-reference)))
                if delta>1e-6 or not np.array_equal(prob>=.5,reference>=.5):raise ValueError('Baseline reproduction failed')
                reproduction.append(dict(path=row['path'],max_difference=delta))
            name=Path(row['path']).stem+'.npy';np.save(out/name,prob);hashes[name]=digest(out/name);probabilities[row['path']]=prob
            print('Reproduced',row['path'],flush=True)
    def evaluate(rows,t,n):
        return [dict(path=r['path'],patient=r['patient'],**score_policy(probabilities[r['path']],r['events'],r['duration_seconds'],t,n)) for r in rows]
    def by_patient(rows):return {patient:aggregate([r for r in rows if r['patient']==patient]) for patient in sorted({r['patient'] for r in rows})}
    baseline=evaluate(train,.5,1);baseline_patients=by_patient(baseline);fitting=[]
    for t in protocol['thresholds']:
        for n in protocol['consecutive_windows']:
            rows=evaluate(train,t,n);patients=by_patient(rows);total=aggregate(rows)
            eligible=all(all(patients[k][m]>=baseline_patients[k][m] for m in ('matched_events','timely_matched_events')) for k in patients)
            fitting.append(dict(threshold=t,consecutive=n,eligible=eligible,metrics=total,patients=patients))
    chosen=min([r for r in fitting if r['eligible']],key=lambda r:(r['metrics']['false_alarm_events'],r['metrics']['background_alarm_seconds'],r['metrics']['maximum_timely_latency_seconds'] or 0,r['consecutive'],r['threshold']))
    save_json(out/'selection.json',dict(fitting=fitting,selected=chosen,validation_used_for_selection=False))
    # The only validation policies scored are the original baseline and fixed choice.
    baseline=evaluate(validation,.5,1);candidate=evaluate(validation,chosen['threshold'],chosen['consecutive'])
    b=aggregate(baseline);c=aggregate(candidate);bp=by_patient(baseline);cp=by_patient(candidate)
    if b['false_alarm_events']!=report['false_alarm_events'] or b['matched_events']!=report['matched_events']:raise ValueError('Baseline event accounting differs')
    checks=dict(false_alarms_lower=c['false_alarm_events']<b['false_alarm_events'],
        matched_events_preserved=all(cp[k]['matched_events']>=bp[k]['matched_events'] for k in bp),
        timely_events_preserved=all(cp[k]['timely_matched_events']>=bp[k]['timely_matched_events'] for k in bp),
        background_alarm_seconds_not_higher=c['background_alarm_seconds']<=b['background_alarm_seconds'])
    save_json(out/'cases.json',dict(baseline=baseline,candidate=candidate))
    save_json(out/'probability-hashes.json',hashes)
    save_json(out/'policy.json',dict(schema_version=1,checkpoint_sha256=report['checkpoint_sha256'],
        threshold=chosen['threshold'],consecutive_windows=chosen['consecutive'],window_seconds=4,
        development_checks_passed=all(checks.values()),independently_qualified=False))
    save_json(out/'summary.json',dict(baseline=b,candidate=c,per_patient=dict(baseline=bp,candidate=cp),checks=checks,
        passed=all(checks.values()),false_alarm_reduction_fraction=1-c['false_alarm_events']/b['false_alarm_events'],
        checkpoint_reproduction=reproduction,recordings=12,independently_qualified=False,
        clinical_ready=False,models_changed=False,protocol_sha256=digest(out/'protocol.json')))
    print(json.dumps(dict(baseline=b,candidate=c,checks=checks,selected=chosen),indent=2))


if __name__=='__main__':main()
