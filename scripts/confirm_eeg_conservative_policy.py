"""Record and verify the fixed two-window follow-up on reused pilot data."""
import argparse,json
from pathlib import Path
import numpy as np
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.eeg_alarms import score_policy,aggregate,confirmed_windows,apply_alarm_policy

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];old=root/'experiments/eeg-pilot-001';probdir=root/'experiments/eeg-alarm-reduction-001'
a.output.mkdir(parents=True,exist_ok=False);read=lambda p:json.loads(p.read_text())
records=read(old/'prepared-manifest.json')['records'];hashes=read(probdir/'probability-hashes.json');baseline_report=read(old/'summary.json')
protocol=dict(checkpoint_sha256=baseline_report['checkpoint_sha256'],threshold=.5,consecutive_windows=2,
    window_seconds=4,recordings=12,selection='Fixed conservative follow-up after prior policy/retraining failures; validation already examined; not an independent confirmation',
    protocol_recorded_after_initial_score=True,retraining=False,refractory=False,
    acceptance='Fewer false alarms and less background alarm duration, with no reduction of matched/timely seizures for either validation patient')
save_json(a.output/'protocol.json',protocol)
if digest(old/'last.pt')!=protocol['checkpoint_sha256']:raise ValueError('Checkpoint changed')
cases=[]
for r in records:
    path=probdir/(Path(r['path']).stem+'.npy')
    if digest(path)!=hashes[path.name]:raise ValueError('Probability changed')
    prob=np.load(path);confirmed=confirmed_windows(prob,.5,2)
    independently_computed=(np.convolve((prob>=.5).astype(int),[1,1],mode='full')[:len(prob)]==2)
    if not np.array_equal(confirmed,independently_computed):raise ValueError('Confirmation replay failed')
    cases.append(dict(path=r['path'],patient=r['patient'],partition=r['partition'],probability_sha256=digest(path),
        baseline=score_policy(prob,r['events'],r['duration_seconds']),candidate=score_policy(prob,r['events'],r['duration_seconds'],.5,2)))
val=[r for r in cases if r['partition']=='validation'];b=aggregate([r['baseline'] for r in val]);c=aggregate([r['candidate'] for r in val])
if b['false_alarm_events']!=722 or b['matched_events']!=4:raise ValueError('Historical baseline differs')
patients={p:{name:aggregate([r[name] for r in val if r['patient']==p]) for name in ('baseline','candidate')} for p in sorted({r['patient'] for r in val})}
checks=dict(false_alarms_lower=c['false_alarm_events']<b['false_alarm_events'],background_burden_lower=c['background_alarm_seconds']<b['background_alarm_seconds'],
    matched_events_preserved=all(v['candidate']['matched_events']>=v['baseline']['matched_events'] for v in patients.values()),
    timely_events_preserved=all(v['candidate']['timely_matched_events']>=v['baseline']['timely_matched_events'] for v in patients.values()))
policy=dict(schema_version=1,checkpoint_sha256=protocol['checkpoint_sha256'],threshold=.5,consecutive_windows=2,window_seconds=4,
    development_checks_passed=all(checks.values()),independently_qualified=False,clinical_ready=False,
    warning='False alarms remain excessive; research pilot only; validation reused')
if all(checks.values()):
    for r in records:apply_alarm_policy(np.load(probdir/(Path(r['path']).stem+'.npy')),policy,protocol['checkpoint_sha256'])
save_json(a.output/'policy.json',policy);save_json(a.output/'cases.json',cases)
save_json(a.output/'summary.json',dict(baseline=b,candidate=c,patients=patients,checks=checks,passed=all(checks.values()),
    false_alarm_reduction_fraction=1-c['false_alarm_events']/b['false_alarm_events'],background_alarm_fraction=c['background_alarm_seconds']/(c['background_hours']*3600),
    remaining_false_alarm_problem=True,independently_qualified=False,clinical_ready=False,validation_reused=True))
save_json(a.output/'verification.json',dict(passed=True,recordings_replayed=len(cases),confirmation_matches_independent_convolution=True,
    summary_sha256=digest(a.output/'summary.json'),policy_sha256=digest(a.output/'policy.json'),
    sources={str(p.relative_to(root)):digest(p) for p in (Path(__file__),root/'src/neurofusion/eeg_alarms.py')}))
print(json.dumps(dict(baseline=b,candidate=c,checks=checks),indent=2))
