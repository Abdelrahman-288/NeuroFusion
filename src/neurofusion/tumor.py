"""BRISC image-level research classifier and explicit four-class metrics."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn

CLASSES=('glioma','meningioma','pituitary','no_tumor')


class TumorCNN(nn.Module):
    def __init__(self):
        super().__init__()
        layers=[]
        for a,b in [(1,16),(16,32),(32,64)]:
            layers.extend([nn.Conv2d(a,b,3,stride=2,padding=1),nn.GroupNorm(4,b),nn.LeakyReLU(.1)])
        self.features=nn.Sequential(*layers,nn.AvgPool2d(4))
        self.head=nn.Linear(64*4*4,4)

    def forward(self,x):
        return self.head(self.features(x).flatten(1))


def load_partition(root,splits,partition):
    if partition not in ('train','validation'):
        raise ValueError('Development loader refuses test and quarantine')
    root=Path(root).resolve()
    document=json.loads(Path(splits).read_text())
    if not document.get('frozen'):
        raise ValueError('Frozen split required')
    active={}
    for row in document['assignments']:
        if row['partition']=='quarantine': continue
        previous=active.setdefault(row['group_id'],row['partition'])
        if previous!=row['partition']: raise ValueError('Group crosses partitions')
    rows=sorted([r for r in document['assignments'] if r['partition']==partition],key=lambda r:r['path'])
    if not rows or len({r['path'] for r in rows})!=len(rows):
        raise ValueError('Empty partition or repeated image path')
    images=np.empty((len(rows),1,128,128),dtype=np.uint8)
    labels=np.empty(len(rows),dtype=np.int64)
    for i,row in enumerate(rows):
        path=(root/row['path']).resolve()
        if not path.is_relative_to(root): raise ValueError('Path escapes dataset root')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Image changed since curation')
        with Image.open(path) as image:
            images[i,0]=np.asarray(image.convert('L').resize((128,128),Image.Resampling.BILINEAR))
        labels[i]=CLASSES.index(row['label'])
    return images,labels,rows


def classification_metrics(labels,probabilities):
    labels=np.asarray(labels)
    probabilities=np.asarray(probabilities)
    if labels.ndim!=1 or len(labels)==0 or probabilities.shape!=(len(labels),4):
        raise ValueError('Expected nonempty labels and four probabilities per image')
    if not np.isin(labels,np.arange(4)).all() or not np.isfinite(probabilities).all() or (probabilities<0).any() or (probabilities>1).any() or not np.allclose(probabilities.sum(1),1,atol=1e-5):
        raise ValueError('Invalid classes or probabilities')
    prediction=probabilities.argmax(1)
    matrix=np.zeros((4,4),dtype=np.int64)
    np.add.at(matrix,(labels.astype(int),prediction),1)
    per_class=[]
    for i,name in enumerate(CLASSES):
        tp=int(matrix[i,i]); support=int(matrix[i].sum()); predicted=int(matrix[:,i].sum())
        per_class.append({'class':name,'support':support,'precision':tp/predicted if predicted else 0.,
                          'recall':tp/support if support else None,'f1':2*tp/(support+predicted) if support+predicted else 0.})
    return {'accuracy':float((prediction==labels).mean()),'macro_f1':float(np.mean([r['f1'] for r in per_class])),
            'balanced_accuracy':float(np.mean([r['recall'] for r in per_class if r['recall'] is not None])),
            'confusion_matrix':matrix.tolist(),'per_class':per_class,'images':len(labels)}
