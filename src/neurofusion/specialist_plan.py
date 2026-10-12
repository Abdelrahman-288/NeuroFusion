"""Patient-disjoint engineering partitions; never creates a clinical test cohort."""
import hashlib
import numpy as np


def numeric_foreground(mask):
    values=np.asarray(mask)
    if values.ndim!=3 or not values.size or not np.isfinite(values).all() or not np.isin(values,[0,1,2,4]).all():
        raise ValueError('Expected finite 3D labels from {0,1,2,4}')
    return np.isin(values,[1,2,4])


def engineering_partition(records, train_patients=16, salt='ucsf-engineering-v1'):
    if len({r['exam_id'] for r in records}) != len(records):
        raise ValueError('Duplicate exam')
    patients=sorted({r['patient_id'] for r in records},key=lambda x:(hashlib.sha256((salt+':'+x).encode()).hexdigest(),x))
    if type(train_patients) is not int or not 0<train_patients<len(patients):
        raise ValueError('Both train and development validation need patients')
    train=set(patients[:train_patients])
    return {'purpose':'Engineering development only; all patients previously used in import/preprocessing QA',
        'test_patients':0,'external_evaluation_ready':False,'salt':salt,
        'train_patients':patients[:train_patients], 'development_validation_patients':patients[train_patients:],
        'records':[{**r,'role':'train' if r['patient_id'] in train else 'development_validation'}
                   for r in sorted(records,key=lambda r:r['exam_id'])]}
