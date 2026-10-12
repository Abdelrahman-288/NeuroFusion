"""Strict CHB-MIT annotation parsing and event-level pilot evaluation."""
import re
import numpy as np

CHANNELS=('FP1-F7','F7-T7','P7-O1','FP2-F8','F8-T8','P8-O2')


def patient_group(case):
    if not re.fullmatch(r'chb\d{2}',case):raise ValueError('Invalid CHB case')
    return 'chb01' if case=='chb21' else case


def parse_summary(text):
    rows=[]
    for block in text.split('File Name: ')[1:]:
        name=block.splitlines()[0].strip()
        if not re.fullmatch(r'chb\d{2}_\d+[a-z+]?\.edf',name):raise ValueError('Unexpected EDF filename')
        count=re.search(r'Number of Seizures in File:\s*(\d+)',block)
        if count is None:raise ValueError('Missing seizure count')
        starts=[float(x) for x in re.findall(r'Seizure(?: \d+)? Start Time:\s*(\d+) seconds',block)]
        ends=[float(x) for x in re.findall(r'Seizure(?: \d+)? End Time:\s*(\d+) seconds',block)]
        if len(starts)!=len(ends) or len(starts)!=int(count[1]):raise ValueError('Incomplete seizure annotations')
        events=list(zip(starts,ends))
        if any(a<0 or b<=a for a,b in events) or any(events[i][0]<events[i-1][1] for i in range(1,len(events))):raise ValueError('Invalid event intervals')
        rows.append({'file':name,'events':events})
    if not rows or len({r['file'] for r in rows})!=len(rows):raise ValueError('Empty or duplicate summary')
    return rows


def event_scores(probabilities,events,duration,window=4.,threshold=.5):
    p=np.asarray(probabilities)
    if p.ndim!=1 or not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not 0<threshold<1:
        raise ValueError('Valid window probabilities required')
    if duration<=0 or window<=0 or len(p)*window>duration+1e-6:raise ValueError('Invalid recording duration')
    if any(not 0<=a<b<=duration for a,b in events):raise ValueError('Events outside recording')
    positive=p>=threshold;intervals=[]
    for i,on in enumerate(positive):
        if on:
            if intervals and intervals[-1][1]==i*window:intervals[-1][1]=(i+1)*window
            else:intervals.append([i*window,(i+1)*window])
    # One-to-one event matching: a long alarm cannot claim several seizures.
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching
    overlap=np.array([[max(a,c)<min(b,d) for c,d in intervals] for a,b in events],dtype=np.int8).reshape(len(events),len(intervals))
    matched=maximum_bipartite_matching(csr_matrix(overlap),perm_type='column') if len(events) and intervals else np.full(len(events),-1)
    tp=int(np.sum(matched>=0))
    background=duration-sum(b-a for a,b in events)
    # Extra split alarms count as false alarms under this explicit matching rule.
    false=len(intervals)-tp
    return {'reference_events':len(events),'predicted_events':len(intervals),'matched_events':tp,'false_alarm_events':false,
            'background_hours':background/3600,'event_sensitivity':tp/len(events) if events else None,
            'false_alarms_per_background_hour':false/(background/3600) if background>0 else None,
            'latency_seconds':[max(0.,intervals[j][0]+window-events[i][0]) for i,j in enumerate(matched) if j>=0],
            'predicted_intervals':intervals,'matching':'maximum-cardinality one-to-one window interval overlap; decisions available at window end, possibly after seizure end; no merging across EDF gaps'}
