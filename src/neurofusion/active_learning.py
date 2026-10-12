"""Deterministic development-only annotation prioritization, not clinical triage."""
import hashlib
import math
import numpy as np


def select_annotations(candidates, *, protected_patients, budget, seed=42, diversity_weight=.5):
    if type(budget) is not int or budget<1:raise ValueError('Positive integer annotation budget required')
    if type(seed) is not int:raise ValueError('Integer seed required')
    if not isinstance(diversity_weight,(int,float)) or not math.isfinite(diversity_weight) or not 0<=diversity_weight<=1:
        raise ValueError('Diversity weight must be within zero and one')
    if not isinstance(protected_patients,(set,list,tuple)) or any(not isinstance(p,str) or not p.strip() for p in protected_patients):
        raise ValueError('Explicit protected patient identifiers required')
    protected=set(protected_patients);seen=set();patients=set();rows=[];dimension=None
    for row in candidates:
        cid=row.get('case_id');patient=row.get('patient_id')
        if any(not isinstance(v,str) or not v.strip() for v in (cid,patient)) or cid in seen:
            raise ValueError('Unique case and nonempty patient identifiers required')
        seen.add(cid)
        if patient in patients:raise ValueError('Group repeat visits into one patient candidate before selection')
        patients.add(patient)
        if patient in protected or row.get('partition')!='train' or row.get('role')!='unlabeled_development':
            raise ValueError('Protected or ineligible patient in annotation pool')
        if row.get('patient_identity_verified') is not True:
            raise ValueError('Verified patient grouping required; image identifiers are insufficient')
        uncertainty=row.get('uncertainty')
        if type(uncertainty) not in (int,float) or not math.isfinite(uncertainty) or not 0<=uncertainty<=1:
            raise ValueError('Finite normalized uncertainty required')
        for key in ('model_sha256','input_sha256','embedding_version','uncertainty_method'):
            value=row.get(key)
            if not isinstance(value,str) or not value.strip():raise ValueError('Selection provenance required: '+key)
        for key in ('model_sha256','input_sha256'):
            if len(row[key])!=64 or any(c not in '0123456789abcdef' for c in row[key]):raise ValueError('SHA256 required')
        try:embedding=np.asarray(row['embedding'],dtype=np.float64)
        except (KeyError,ValueError,TypeError) as error:raise ValueError('Numeric embedding required') from error
        if embedding.ndim!=1 or not 1<=len(embedding)<=4096 or not np.isfinite(embedding).all() or np.linalg.norm(embedding)==0:
            raise ValueError('Finite nonzero one-dimensional embedding required')
        if dimension is None:dimension=len(embedding)
        if dimension!=len(embedding):raise ValueError('Embedding dimensions differ')
        rows.append((dict(row),embedding/np.linalg.norm(embedding)))
    if budget>len(rows):raise ValueError('Budget exceeds eligible patients')
    if len({r['embedding_version'] for r,_ in rows})!=1 or len({r['model_sha256'] for r,_ in rows})!=1 or len({r['uncertainty_method'] for r,_ in rows})!=1:
        raise ValueError('Comparable embeddings, model and uncertainty method required')
    tie=lambda r:hashlib.sha256(f'{seed}:{r["case_id"]}'.encode()).hexdigest()
    rows.sort(key=lambda pair:tie(pair[0]));remaining=list(range(len(rows)));selected=[];result=[]
    while len(selected)<budget:
        scores=[]
        for i in remaining:
            row,vector=rows[i]
            distance=min(float(np.clip((1-np.dot(vector,rows[j][1]))/2,0,1)) for j in selected) if selected else 0.
            score=(1-diversity_weight)*row['uncertainty']+diversity_weight*distance
            scores.append((score,i,distance))
        score,i,distance=max(scores,key=lambda item:item[0])
        selected.append(i);remaining.remove(i);row=rows[i][0]
        result.append({k:v for k,v in row.items() if k!='embedding'}|{'rank':len(selected),'selection_score':score,
            'distance_to_selected':distance,'reason':'normalized uncertainty plus cosine-distance diversity',
            'annotation_status':'unassigned','approved_for_training':False})
    random_order=sorted((r for r,_ in rows),key=lambda r:hashlib.sha256(f'random:{seed}:{r["case_id"]}'.encode()).hexdigest())
    return {'strategy':'uncertainty_cosine_greedy_v1','seed':seed,'budget':budget,'pool_size':len(rows),
            'diversity_weight':diversity_weight,'selected':result,
            'random_comparator_case_ids':[r['case_id'] for r in random_order[:budget]],
            'protected_patients_checked':len(protected),'clinical_urgency':False,
            'benchmark_completed':False,'training_export_permitted':False,
            'note':'Selection only. Equal-budget annotation and held-out performance comparison remain required.'}
