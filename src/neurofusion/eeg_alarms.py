"""Causal EEG alarm confirmation without look-ahead or refractory suppression."""
import numpy as np
from neurofusion.eeg import event_scores


def normalize_windows(windows):
    x=np.asarray(windows,dtype=np.float32)
    if x.ndim!=3 or x.shape[1:]!=(6,512) or not np.isfinite(x).all():raise ValueError('Expected finite six-channel four-second EEG windows')
    centered=x-x.mean(axis=2,keepdims=True)
    scale=np.sqrt(np.mean(centered**2,axis=2,keepdims=True))
    return np.clip(centered/np.maximum(scale,.01),-8,8).astype(np.float32)


def confirmed_windows(probabilities,threshold,consecutive):
    p=np.asarray(probabilities)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not 0<threshold<1 or type(consecutive) is not int or not 1<=consecutive<=8:
        raise ValueError('Invalid probabilities or alarm policy')
    active=np.zeros(len(p),dtype=np.float32);run=0
    for i,value in enumerate(p):
        run=run+1 if value>=threshold else 0
        active[i]=float(run>=consecutive)
    return active


def apply_alarm_policy(probabilities,policy,checkpoint_sha256):
    if policy.get('schema_version')!=1 or policy.get('checkpoint_sha256')!=checkpoint_sha256 or policy.get('window_seconds')!=4:
        raise ValueError('Alarm policy is not compatible with this checkpoint/window size')
    if policy.get('development_checks_passed') is not True:raise ValueError('Alarm policy failed development checks')
    return confirmed_windows(probabilities,policy['threshold'],policy['consecutive_windows'])


def score_policy(probabilities,events,duration,threshold=.5,consecutive=1):
    active=confirmed_windows(probabilities,threshold,consecutive)
    result=event_scores(active,events,duration)
    # Historical overlap metrics are retained. Count timely matches separately
    # using decision availability, not a backdated start of confirmation.
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching
    alarms=result['predicted_intervals']
    overlap=np.array([[max(a,start+4)<min(b,end+4) for start,end in alarms] for a,b in events],dtype=np.int8).reshape(len(events),len(alarms))
    matched=maximum_bipartite_matching(csr_matrix(overlap),perm_type='column') if events and alarms else np.full(len(events),-1)
    result['timely_matched_events']=int((matched>=0).sum())
    result['timely_latency_seconds']=[max(0.,alarms[j][0]+4-events[i][0]) for i,j in enumerate(matched) if j>=0]
    result['alarm_seconds']=float(active.sum()*4)
    result['background_alarm_seconds']=float(sum(max(0.,min((i+2)*4,duration)-(i+1)*4)-sum(max(0.,min((i+2)*4,duration,b)-max((i+1)*4,a)) for a,b in events) for i,on in enumerate(active) if on))
    result['decision_times_seconds']=[a+4 for a,b in alarms]
    return result


def aggregate(rows):
    totals={k:sum(r[k] for r in rows) for k in ('reference_events','matched_events','timely_matched_events','false_alarm_events','background_hours','alarm_seconds','background_alarm_seconds')}
    totals['false_alarms_per_background_hour']=totals['false_alarm_events']/totals['background_hours'] if totals['background_hours'] else None
    totals['event_sensitivity']=totals['matched_events']/totals['reference_events'] if totals['reference_events'] else None
    latencies=[v for r in rows for v in r['timely_latency_seconds']]
    totals['maximum_timely_latency_seconds']=max(latencies) if latencies else None
    totals['median_timely_latency_seconds']=float(np.median(latencies)) if latencies else None
    return totals
